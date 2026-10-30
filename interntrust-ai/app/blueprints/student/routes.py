import json
import os

from flask import render_template, redirect, url_for, flash, request, current_app, send_file, abort, jsonify
from flask_login import login_required, current_user

from app.extensions import db, limiter
from app.models import Analysis, AnalysisSignal, RiskSignal, Report, ChecklistProgress
from app.blueprints.student import student_bp
from app.blueprints.student.forms import AnalyzerForm, ProfileForm, ChangePasswordForm
from app.services.risk_engine import run_rule_based_analysis, default_verification_checklist
from app.services.file_processing import is_allowed_file, save_uploaded_file, extract_text_from_file
from app.services import ai_engine
from app.services.pdf_report import generate_analysis_pdf
from app.utils import student_required


@student_bp.route("/")
@login_required
@student_required
def dashboard():
    base_query = Analysis.query.filter_by(user_id=current_user.id)
    total = base_query.count()
    low = base_query.filter_by(risk_level="Low").count()
    medium = base_query.filter_by(risk_level="Medium").count()
    high = base_query.filter_by(risk_level="High").count()
    recent = base_query.order_by(Analysis.created_at.desc()).limit(5).all()

    return render_template(
        "student/dashboard.html",
        total=total, low=low, medium=medium, high=high, recent=recent,
    )


@student_bp.route("/analyze", methods=["GET", "POST"])
@login_required
@student_required
@limiter.limit("20 per hour")
def analyze():
    form = AnalyzerForm()

    if form.validate_on_submit():
        data = {
            "opportunity_type": form.opportunity_type.data,
            "opportunity_title": form.opportunity_title.data.strip(),
            "company_name": (form.company_name.data or "").strip(),
            "company_url": (form.company_url.data or "").strip(),
            "recruiter_name": (form.recruiter_name.data or "").strip(),
            "recruiter_email": (form.recruiter_email.data or "").strip(),
            "work_mode": form.work_mode.data or "",
            "stipend_or_salary": (form.stipend_or_salary.data or "").strip(),
            "description": (form.description.data or "").strip(),
            "recruiter_message": (form.recruiter_message.data or "").strip(),
        }

        # --- Safe file upload handling ---
        stored_filename = None
        extracted_text = ""
        uploaded_file = form.document.data
        if uploaded_file and uploaded_file.filename:
            if not is_allowed_file(uploaded_file.filename, current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]):
                flash("Unsupported file type. Please upload a PDF, DOCX, or TXT file.", "danger")
                return render_template("student/analyze.html", form=form)
            stored_filename, abs_path = save_uploaded_file(uploaded_file, current_app.config["UPLOAD_FOLDER"])
            if stored_filename:
                extracted_text = extract_text_from_file(abs_path)

        data["extracted_text"] = extracted_text

        # --- Rule-based engine (always runs) ---
        active_signals = {s.signal_code: s for s in RiskSignal.query.filter_by(is_active=True).all()}
        thresholds = {
            "low_max": current_app.config["RISK_LOW_MAX"],
            "medium_max": current_app.config["RISK_MEDIUM_MAX"],
        }
        result = run_rule_based_analysis(data, active_signals, thresholds)

        analysis_source = "rule_based"
        ai_summary = None
        signal_explanations = {}

        # --- Optional AI layer ---
        if ai_engine.is_available():
            success, ai_result, _err = ai_engine.generate_ai_explanation(data, result["findings"])
            if success and ai_result:
                analysis_source = "ai_assisted"
                ai_summary = ai_result.get("summary")
                signal_explanations = ai_result.get("signal_explanations", {}) or {}

        if not ai_summary:
            ai_summary = _fallback_summary(data, result)

        # --- Persist analysis ---
        analysis = Analysis(
            user_id=current_user.id,
            opportunity_type=data["opportunity_type"],
            opportunity_title=data["opportunity_title"],
            company_name=data["company_name"] or None,
            company_url=data["company_url"] or None,
            recruiter_name=data["recruiter_name"] or None,
            recruiter_email=data["recruiter_email"] or None,
            work_mode=data["work_mode"] or None,
            stipend_or_salary=data["stipend_or_salary"] or None,
            description=data["description"] or None,
            recruiter_message=data["recruiter_message"] or None,
            uploaded_filename=stored_filename,
            extracted_text=extracted_text or None,
            risk_score=result["score"],
            risk_level=result["level"],
            analysis_source=analysis_source,
            analysis_summary=ai_summary,
            positive_indicators=json.dumps(result["positive_indicators"]),
            missing_information=json.dumps(result["missing_information"]),
        )
        db.session.add(analysis)
        db.session.flush()  # get analysis.id before commit

        for f in result["findings"]:
            explanation = signal_explanations.get(f["code"]) or f["explanation"]
            signal_row = active_signals.get(f["code"])
            db.session.add(AnalysisSignal(
                analysis_id=analysis.id,
                risk_signal_id=signal_row.id if signal_row else None,
                signal_name=f["name"],
                observed_value=str(f["observed_value"])[:300],
                explanation=explanation,
                score_contribution=f["weight"],
            ))

        for item in default_verification_checklist():
            db.session.add(ChecklistProgress(analysis_id=analysis.id, checklist_item=item))

        db.session.commit()
        flash("Analysis complete.", "success")
        return redirect(url_for("student.results", analysis_id=analysis.id))

    return render_template("student/analyze.html", form=form)


def _fallback_summary(data, result):
    title = data.get("opportunity_title") or "This opportunity"
    company = data.get("company_name") or "an unspecified company"
    count = len(result["findings"])
    if count == 0:
        return f"{title} at {company} did not trigger any configured warning signs in the rule-based engine."
    return (
        f"{title} at {company} triggered {count} potential warning sign(s) in the rule-based engine, "
        f"resulting in a {result['level'].lower()} risk classification. Review the details below before proceeding."
    )


def _get_owned_analysis_or_404(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)
    return analysis


@student_bp.route("/results/<int:analysis_id>")
@login_required
@student_required
def results(analysis_id):
    analysis = _get_owned_analysis_or_404(analysis_id)
    positive_indicators = json.loads(analysis.positive_indicators or "[]")
    missing_information = json.loads(analysis.missing_information or "[]")
    checklist_items = analysis.checklist_items.order_by(ChecklistProgress.id.asc()).all()
    return render_template(
        "student/results.html",
        analysis=analysis,
        positive_indicators=positive_indicators,
        missing_information=missing_information,
        checklist_items=checklist_items,
    )


@student_bp.route("/history")
@login_required
@student_required
def history():
    page = request.args.get("page", 1, type=int)
    risk_filter = request.args.get("risk", "")
    type_filter = request.args.get("type", "")
    search = request.args.get("q", "").strip()

    query = Analysis.query.filter_by(user_id=current_user.id)
    if risk_filter in ("Low", "Medium", "High"):
        query = query.filter_by(risk_level=risk_filter)
    if type_filter in ("internship", "job"):
        query = query.filter_by(opportunity_type=type_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(Analysis.opportunity_title.ilike(like), Analysis.company_name.ilike(like))
        )

    pagination = query.order_by(Analysis.created_at.desc()).paginate(page=page, per_page=8, error_out=False)

    return render_template(
        "student/history.html",
        pagination=pagination,
        risk_filter=risk_filter,
        type_filter=type_filter,
        search=search,
    )


@student_bp.route("/history/<int:analysis_id>/delete", methods=["POST"])
@login_required
@student_required
def delete_analysis(analysis_id):
    analysis = _get_owned_analysis_or_404(analysis_id)
    db.session.delete(analysis)
    db.session.commit()
    flash("Analysis deleted.", "info")
    return redirect(url_for("student.history"))


@student_bp.route("/results/<int:analysis_id>/report.pdf")
@login_required
@student_required
def download_report(analysis_id):
    analysis = _get_owned_analysis_or_404(analysis_id)

    filename = f"report_{analysis.id}_{current_user.id}.pdf"
    output_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "instance",
    "reports",
    filename
)
    findings = [
        {"name": s.signal_name, "category": (s.risk_signal.category if s.risk_signal else "general"),
         "explanation": s.explanation, "weight": s.score_contribution}
        for s in analysis.signals
    ]
    positive_indicators = json.loads(analysis.positive_indicators or "[]")
    missing_information = json.loads(analysis.missing_information or "[]")
    checklist_items = analysis.checklist_items.order_by(ChecklistProgress.id.asc()).all()

    generate_analysis_pdf(
        analysis, current_user, findings, positive_indicators, missing_information, checklist_items, output_path
    )

    existing = Report.query.filter_by(analysis_id=analysis.id).first()
    if existing:
        existing.report_path = output_path
    else:
        db.session.add(Report(analysis_id=analysis.id, report_path=output_path))
    db.session.commit()

    return send_file(output_path, as_attachment=True, download_name=f"InternTrust_Report_{analysis.id}.pdf")


@student_bp.route("/checklist/<int:item_id>/update", methods=["POST"])
@login_required
@student_required
def update_checklist_item(item_id):
    item = ChecklistProgress.query.get_or_404(item_id)
    if item.analysis.user_id != current_user.id:
        abort(403)
    new_status = request.form.get("status")
    if new_status not in ("not_checked", "verified", "needs_attention"):
        abort(400)
    item.status = new_status
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "status": item.status})
    return redirect(url_for("student.results", analysis_id=item.analysis_id))


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@student_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if "update_profile" in request.form and form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", form=form, password_form=password_form)


@student_bp.route("/profile/change-password", methods=["POST"])
@login_required
@student_required
def change_password():
    password_form = ChangePasswordForm()
    profile_form = ProfileForm(obj=current_user)

    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("student.profile"))

    return render_template("student/profile.html", form=profile_form, password_form=password_form)

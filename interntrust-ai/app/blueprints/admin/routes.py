from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Analysis, RiskSignal, AdminActivityLog
from app.blueprints.admin import admin_bp
from app.utils import admin_required


def _log(action, details=""):
    db.session.add(AdminActivityLog(admin_id=current_user.id, action=action, details=details))


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total_students = User.query.filter_by(role="student").count()
    total_analyses = Analysis.query.count()
    low = Analysis.query.filter_by(risk_level="Low").count()
    medium = Analysis.query.filter_by(risk_level="Medium").count()
    high = Analysis.query.filter_by(risk_level="High").count()
    recent_analyses = Analysis.query.order_by(Analysis.created_at.desc()).limit(8).all()
    recent_activity = AdminActivityLog.query.order_by(AdminActivityLog.created_at.desc()).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        total_students=total_students, total_analyses=total_analyses,
        low=low, medium=medium, high=high,
        recent_analyses=recent_analyses, recent_activity=recent_activity,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = User.query.filter_by(role="student")
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/users.html", pagination=pagination, search=search)


@admin_bp.route("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id):
    student = User.query.get_or_404(user_id)
    analyses = Analysis.query.filter_by(user_id=student.id).order_by(Analysis.created_at.desc()).all()
    return render_template("admin/user_detail.html", student=student, analyses=analyses)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    student = User.query.get_or_404(user_id)
    student.is_active_account = not student.is_active_account
    _log(
        "Deactivated student" if not student.is_active_account else "Reactivated student",
        details=f"user_id={student.id}, email={student.email}",
    )
    db.session.commit()
    flash(f"Account {'deactivated' if not student.is_active_account else 'reactivated'} for {student.email}.", "info")
    return redirect(url_for("admin.user_detail", user_id=student.id))


@admin_bp.route("/analyses")
@login_required
@admin_required
def analyses():
    search = request.args.get("q", "").strip()
    risk_filter = request.args.get("risk", "")
    page = request.args.get("page", 1, type=int)

    query = Analysis.query
    if risk_filter in ("Low", "Medium", "High"):
        query = query.filter_by(risk_level=risk_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(Analysis.opportunity_title.ilike(like), Analysis.company_name.ilike(like))
        )

    pagination = query.order_by(Analysis.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/analyses.html", pagination=pagination, search=search, risk_filter=risk_filter)


@admin_bp.route("/analyses/<int:analysis_id>")
@login_required
@admin_required
def analysis_detail(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    _log("Viewed analysis detail", details=f"analysis_id={analysis.id}")
    db.session.commit()
    return render_template("admin/analysis_detail.html", analysis=analysis)


@admin_bp.route("/risk-signals")
@login_required
@admin_required
def risk_signals():
    signals = RiskSignal.query.order_by(RiskSignal.category.asc(), RiskSignal.signal_name.asc()).all()
    return render_template("admin/signals.html", signals=signals)


@admin_bp.route("/risk-signals/<int:signal_id>/update", methods=["POST"])
@login_required
@admin_required
def update_risk_signal(signal_id):
    signal = RiskSignal.query.get_or_404(signal_id)

    is_active = request.form.get("is_active") == "on"
    weight_raw = request.form.get("default_weight", "").strip()

    try:
        weight = int(weight_raw)
        if weight < 0 or weight > 100:
            raise ValueError
    except ValueError:
        flash("Weight must be a whole number between 0 and 100.", "danger")
        return redirect(url_for("admin.risk_signals"))

    signal.is_active = is_active
    signal.default_weight = weight
    _log("Updated risk signal", details=f"{signal.signal_code}: active={is_active}, weight={weight}")
    db.session.commit()
    flash(f"Updated '{signal.signal_name}'.", "success")
    return redirect(url_for("admin.risk_signals"))

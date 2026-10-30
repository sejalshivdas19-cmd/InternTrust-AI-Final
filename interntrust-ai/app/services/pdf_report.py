import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

BRAND_PURPLE = colors.HexColor("#7c3aed")
BRAND_DARK = colors.HexColor("#12081f")
RISK_COLORS = {"Low": colors.HexColor("#16a34a"), "Medium": colors.HexColor("#d97706"), "High": colors.HexColor("#dc2626")}
RISK_HEX = {"Low": "#16a34a", "Medium": "#d97706", "High": "#dc2626"}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", fontSize=20, textColor=BRAND_PURPLE, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Tagline", fontSize=9, textColor=colors.grey, spaceAfter=14))
    styles.add(ParagraphStyle(name="SectionHeading", fontSize=13, textColor=BRAND_DARK, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="Small", fontSize=8, textColor=colors.grey))
    return styles


def generate_analysis_pdf(analysis, student, findings, positive_indicators, missing_information, checklist_items, output_path):
    """Builds a professional PDF risk report and writes it to output_path."""
    styles = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"InternTrust AI Report #{analysis.id}",
    )
    story = []

    story.append(Paragraph("InternTrust AI", styles["BrandTitle"]))
    story.append(Paragraph("Don't Trust Every Internship. Verify It.", styles["Tagline"]))
    story.append(HRFlowable(width="100%", color=BRAND_PURPLE, thickness=1))
    story.append(Spacer(1, 10))

    meta_table = Table([
        ["Report ID", f"INTAI-{analysis.id:06d}"],
        ["Generated", datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")],
        ["Analysis Date", analysis.created_at.strftime("%d %b %Y, %H:%M UTC") if analysis.created_at else "-"],
        ["Prepared For", student.full_name],
    ], colWidths=[100, 380])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Opportunity Details", styles["SectionHeading"]))
    details = [
        ["Title", analysis.opportunity_title or "-"],
        ["Type", (analysis.opportunity_type or "-").title()],
        ["Company", analysis.company_name or "Not provided"],
        ["Website / URL", analysis.company_url or "Not provided"],
        ["Recruiter", analysis.recruiter_name or "Not provided"],
        ["Recruiter Email", analysis.recruiter_email or "Not provided"],
        ["Work Mode", analysis.work_mode or "Not specified"],
        ["Salary / Stipend", analysis.stipend_or_salary or "Not provided"],
    ]
    details_table = Table(details, colWidths=[110, 370])
    details_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#eeeeee")),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Risk Assessment", styles["SectionHeading"]))
    risk_hex = RISK_HEX.get(analysis.risk_level, "#666666")
    score_table = Table([[
        Paragraph(f"<b>Risk Score:</b> {analysis.risk_score} / 100", styles["Body"]),
        Paragraph(f'<font color="{risk_hex}"><b>{analysis.risk_level.upper()} RISK</b></font>', styles["Body"]),
    ]], colWidths=[240, 240])
    story.append(score_table)
    story.append(Paragraph(
        f"Analysis source: {'AI-assisted (rule-based engine + AI explanation)' if analysis.analysis_source == 'ai_assisted' else 'Rule-based engine only'}",
        styles["Small"]
    ))
    story.append(Spacer(1, 8))

    if analysis.analysis_summary:
        story.append(Paragraph("<b>Summary</b>", styles["Body"]))
        story.append(Paragraph(analysis.analysis_summary, styles["Body"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Detected Warning Signs", styles["SectionHeading"]))
    if findings:
        rows = [["Signal", "Category", "Explanation", "Weight"]]
        for f in findings:
            rows.append([
                Paragraph(f.get("name", f.get("signal_name", "-")), styles["Body"]),
                Paragraph((f.get("category") or "-").title(), styles["Body"]),
                Paragraph(f.get("explanation", "-"), styles["Body"]),
                str(f.get("weight", f.get("score_contribution", "-"))),
            ])
        signal_table = Table(rows, colWidths=[110, 70, 250, 40], repeatRows=1)
        signal_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f5fb")]),
        ]))
        story.append(signal_table)
    else:
        story.append(Paragraph("No specific warning signs were detected in the submitted information.", styles["Body"]))
    story.append(Spacer(1, 12))

    if positive_indicators:
        story.append(Paragraph("Positive / Reassuring Indicators", styles["SectionHeading"]))
        for item in positive_indicators:
            story.append(Paragraph(f"&bull; {item}", styles["Body"]))
        story.append(Spacer(1, 8))

    if missing_information:
        story.append(Paragraph("Missing Information", styles["SectionHeading"]))
        for item in missing_information:
            story.append(Paragraph(f"&bull; {item}", styles["Body"]))
        story.append(Spacer(1, 8))

    if checklist_items:
        story.append(Paragraph("Verification Checklist Status", styles["SectionHeading"]))
        rows = [["Item", "Status"]]
        for item in checklist_items:
            rows.append([Paragraph(item.checklist_item, styles["Body"]), item.status.replace("_", " ").title()])
        checklist_table = Table(rows, colWidths=[380, 90], repeatRows=1)
        checklist_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ]))
        story.append(checklist_table)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=0.6))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This report reflects an automated assessment of the information submitted by the "
        "user and configured detection rules. It is NOT proof that an opportunity is fraudulent or legitimate. "
        "Always independently verify any internship or job opportunity before making payments or sharing "
        "personal information.",
        styles["Small"]
    ))
    story.append(Paragraph(
        f"Generated by InternTrust AI on {datetime.utcnow().strftime('%d %b %Y at %H:%M UTC')}.",
        styles["Small"]
    ))

    doc.build(story)
    return output_path

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, PasswordField
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo


class AnalyzerForm(FlaskForm):
    opportunity_type = SelectField(
        "Opportunity Type", choices=[("internship", "Internship"), ("job", "Job")], validators=[DataRequired()]
    )
    opportunity_title = StringField("Internship / Job Title", validators=[DataRequired(), Length(max=200)])
    company_name = StringField("Company Name", validators=[Optional(), Length(max=200)])
    company_url = StringField("Company Website / Opportunity URL", validators=[Optional(), Length(max=500)])
    recruiter_name = StringField("Recruiter Name", validators=[Optional(), Length(max=150)])
    recruiter_email = StringField("Recruiter Email", validators=[Optional(), Email(), Length(max=180)])
    work_mode = SelectField(
        "Work Mode",
        choices=[
            ("", "Not specified"),
            ("wfh", "Work From Home"),
            ("hybrid", "Hybrid"),
            ("onsite", "On-site"),
        ],
        validators=[Optional()],
    )
    stipend_or_salary = StringField("Salary or Stipend (optional)", validators=[Optional(), Length(max=120)])
    description = TextAreaField("Full Internship or Job Description", validators=[Optional(), Length(max=10000)])
    recruiter_message = TextAreaField("Recruiter Message", validators=[Optional(), Length(max=6000)])
    document = FileField(
        "Optional Document Upload",
        validators=[Optional(), FileAllowed(["pdf", "docx", "txt"], "PDF, DOCX, and TXT files only.")],
    )


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")]
    )

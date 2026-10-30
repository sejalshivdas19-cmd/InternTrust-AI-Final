from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    """Student / job-seeker account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = db.relationship("Analysis", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # Flask-Login uses get_id(); prefix so admins and students never collide
    def get_id(self):
        return f"user:{self.id}"

    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<User {self.email}>"


class Admin(UserMixin, db.Model):
    """Administrator account, kept in a separate table from students so that
    a compromised/duplicated student record can never be granted admin
    privileges by mistake."""

    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def get_id(self):
        return f"admin:{self.id}"

    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<Admin {self.email}>"


class RiskSignal(db.Model):
    """Configurable risk signal definition used by the rule-based engine."""

    __tablename__ = "risk_signals"

    id = db.Column(db.Integer, primary_key=True)
    signal_code = db.Column(db.String(60), unique=True, nullable=False)
    signal_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="general")
    description = db.Column(db.Text, nullable=False, default="")
    default_weight = db.Column(db.Integer, nullable=False, default=10)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Analysis(db.Model):
    """A single submitted opportunity and its computed risk assessment."""

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    opportunity_type = db.Column(db.String(20), nullable=False)  # internship / job
    opportunity_title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=True)
    company_url = db.Column(db.String(500), nullable=True)
    recruiter_name = db.Column(db.String(150), nullable=True)
    recruiter_email = db.Column(db.String(180), nullable=True)
    work_mode = db.Column(db.String(30), nullable=True)
    stipend_or_salary = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    recruiter_message = db.Column(db.Text, nullable=True)

    uploaded_filename = db.Column(db.String(255), nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)

    risk_score = db.Column(db.Integer, nullable=False, default=0)
    risk_level = db.Column(db.String(20), nullable=False, default="Low")
    analysis_source = db.Column(db.String(20), nullable=False, default="rule_based")  # rule_based / ai_assisted
    analysis_summary = db.Column(db.Text, nullable=True)
    positive_indicators = db.Column(db.Text, nullable=True)  # JSON-encoded list
    missing_information = db.Column(db.Text, nullable=True)  # JSON-encoded list

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    signals = db.relationship("AnalysisSignal", backref="analysis", lazy="joined", cascade="all, delete-orphan")
    report = db.relationship("Report", backref="analysis", uselist=False, cascade="all, delete-orphan")
    checklist_items = db.relationship(
        "ChecklistProgress", backref="analysis", lazy="dynamic", cascade="all, delete-orphan"
    )


class AnalysisSignal(db.Model):
    """A specific risk signal detected within one analysis."""

    __tablename__ = "analysis_signals"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_signal_id = db.Column(db.Integer, db.ForeignKey("risk_signals.id"), nullable=True)
    signal_name = db.Column(db.String(150), nullable=False)
    observed_value = db.Column(db.String(300), nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    score_contribution = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    risk_signal = db.relationship("RiskSignal")


class Report(db.Model):
    """Metadata for a generated PDF report."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True)
    report_path = db.Column(db.String(400), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChecklistProgress(db.Model):
    """Verification-assistant checklist item progress for one analysis."""

    __tablename__ = "checklist_progress"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_item = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="not_checked")  # not_checked/verified/needs_attention
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminActivityLog(db.Model):
    """Audit trail of important administrator actions."""

    __tablename__ = "admin_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("Admin")

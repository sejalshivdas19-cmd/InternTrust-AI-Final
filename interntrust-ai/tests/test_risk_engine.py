from app.models import RiskSignal
from app.services.risk_engine import run_rule_based_analysis


def _active_signals():
    return {s.signal_code: s for s in RiskSignal.query.filter_by(is_active=True).all()}


def test_clean_opportunity_scores_low(app):
    with app.app_context():
        data = {
            "opportunity_title": "Backend Development Intern",
            "company_name": "Acme Technologies",
            "company_url": "https://acmetechnologies.com/careers",
            "recruiter_name": "Priya Sharma",
            "recruiter_email": "priya.sharma@acmetechnologies.com",
            "stipend_or_salary": "\u20b915,000/month",
            "description": "You will work with our backend team building REST APIs using Python and Flask.",
            "recruiter_message": "Thanks for applying! Please find the interview schedule attached.",
            "extracted_text": "",
        }
        result = run_rule_based_analysis(data, _active_signals())
        assert result["level"] == "Low"
        assert result["score"] < 30


def test_payment_request_raises_risk(app):
    with app.app_context():
        data = {
            "opportunity_title": "Work From Home Data Entry",
            "company_name": "QuickCash Ventures",
            "company_url": "",
            "recruiter_name": "",
            "recruiter_email": "recruiter123@gmail.com",
            "stipend_or_salary": "Earn \u20b950,000 per week working 1 hour a day",
            "description": "Pay a registration fee of \u20b91500 to secure your slot. Limited slots, act now!",
            "recruiter_message": "Please pay via UPI immediately to confirm your seat, otherwise you will lose this opportunity.",
            "extracted_text": "",
        }
        result = run_rule_based_analysis(data, _active_signals())
        assert result["score"] > 60
        assert result["level"] == "High"
        codes = {f["code"] for f in result["findings"]}
        assert "REGISTRATION_FEE" in codes
        assert "SUSPICIOUS_PAYMENT_CHANNEL" in codes
        assert "UNREALISTIC_PROMISES" in codes


def test_missing_information_is_reported(app):
    with app.app_context():
        data = {
            "opportunity_title": "Marketing Intern",
            "company_name": "",
            "company_url": "",
            "recruiter_name": "",
            "recruiter_email": "",
            "stipend_or_salary": "",
            "description": "",
            "recruiter_message": "",
            "extracted_text": "",
        }
        result = run_rule_based_analysis(data, _active_signals())
        assert "Company website or opportunity URL" in result["missing_information"]
        assert "Recruiter email address" in result["missing_information"]


def test_score_is_clamped_between_0_and_100(app):
    with app.app_context():
        data = {
            "opportunity_title": "Suspicious Offer",
            "description": (
                "registration fee training fee security deposit interview fee pay before joining "
                "upi paytm crypto act now limited slots guaranteed job 100% placement "
                "lose this opportunity blacklist bank account number aadhaar otp"
            ),
            "recruiter_message": "",
            "extracted_text": "",
        }
        result = run_rule_based_analysis(data, _active_signals())
        assert 0 <= result["score"] <= 100

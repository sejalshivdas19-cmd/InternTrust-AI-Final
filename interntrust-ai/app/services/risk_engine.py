"""
Rule-based Risk Assessment Engine
==================================

This module is intentionally independent of any external API so that the
core value of InternTrust AI (risk detection + explanation) always works,
even with zero configuration.

Design principles (see README.md "Scoring Methodology" for full detail):
  * Every detected signal contributes a documented, configurable weight.
  * The engine never claims certainty - it reports *indicators*, not proof.
  * Signals are grouped by category (payment, communication, company, url)
    so results can be explained clearly to a student.
  * The final score is clamped to 0-100 and mapped to Low/Medium/High using
    thresholds that administrators can adjust.
"""

import re
from urllib.parse import urlparse

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com",
    "protonmail.com", "icloud.com", "aol.com", "live.com",
}

PAYMENT_KEYWORDS = {
    "REGISTRATION_FEE": [r"registration fee", r"registration charge", r"register.{0,15}pay", r"reg\.? fee"],
    "TRAINING_FEE": [r"training fee", r"course fee", r"pay for training", r"mandatory training.{0,20}fee"],
    "SECURITY_DEPOSIT": [r"security deposit", r"refundable deposit", r"deposit amount"],
    "INTERVIEW_FEE": [r"interview fee", r"pay.{0,15}interview", r"shortlisting fee"],
    "PAY_BEFORE_JOINING": [r"pay before joining", r"advance payment", r"pay.{0,15}before.{0,15}start"],
    "SUSPICIOUS_PAYMENT_CHANNEL": [r"\bupi\b", r"paytm", r"google pay", r"phonepe", r"crypto", r"bitcoin", r"wallet transfer", r"western union"],
}

COMMUNICATION_KEYWORDS = {
    "URGENCY_PRESSURE": [r"act now", r"limited slots", r"only \d+ (seats|slots)", r"today only", r"urgent(ly)?", r"immediately pay", r"within \d+ hours"],
    "UNREALISTIC_PROMISES": [r"guaranteed job", r"100% placement", r"earn \u20b9?\$?\d{4,}.{0,20}per (day|week)", r"no experience.{0,20}high salary", r"work \d? ?hours?.{0,20}earn"],
    "THREATENING_LANGUAGE": [r"lose (this|the) opportunity", r"blacklist", r"legal action if you.{0,20}(quit|leave)", r"forfeit"],
    "SENSITIVE_INFO_REQUEST": [r"bank account number", r"aadhaar", r"passport number", r"otp", r"credit card number", r"cvv", r"account password"],
}


def _text_corpus(data):
    parts = [
        data.get("opportunity_title", ""),
        data.get("company_name", ""),
        data.get("description", ""),
        data.get("recruiter_message", ""),
        data.get("stipend_or_salary", ""),
        data.get("extracted_text", "") or "",
    ]
    return "\n".join(p for p in parts if p).lower()


def _find_keyword_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _check_url_signals(url):
    findings = []
    if not url:
        return findings

    url = url.strip()
    parsed = urlparse(url if "://" in url else f"http://{url}")
    domain = (parsed.netloc or parsed.path).lower().split("/")[0].split(":")[0]

    if not domain or "." not in domain:
        findings.append(("INVALID_URL", url, "The provided URL does not look like a valid, complete web address."))
        return findings

    for shortener in URL_SHORTENERS:
        if shortener in domain:
            findings.append(("URL_SHORTENER", domain, f"The link uses the '{shortener}' shortening service, which hides the real destination."))
            break

    suspicious_pattern = re.search(r"(secure|verify|update|account)[-.]?\w*\.(?!com$|in$|org$|co$)", domain)
    if suspicious_pattern and domain.count("-") >= 2:
        findings.append(("SUSPICIOUS_URL_PATTERN", domain, "The domain contains patterns (extra hyphens/keywords) sometimes used to imitate official sites."))

    return findings


def _check_company_url_match(company_name, url):
    if not company_name or not url:
        return []
    parsed = urlparse(url if "://" in url else f"http://{url}")
    domain = (parsed.netloc or parsed.path).lower()
    domain_core = re.sub(r"^(www\.)|(\.(com|in|org|net|co|io)(\.\w+)?$)", "", domain)
    company_slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    domain_slug = re.sub(r"[^a-z0-9]", "", domain_core)
    if not domain_slug or not company_slug:
        return []
    # Very small overlap between the two names is a soft signal, not proof.
    if company_slug[:4] not in domain_slug and domain_slug[:4] not in company_slug:
        return [("COMPANY_URL_MISMATCH", domain, "The website domain does not resemble the stated company name.")]
    return []


def _check_recruiter_email(recruiter_email, company_url):
    findings = []
    if not recruiter_email or "@" not in recruiter_email:
        return findings
    email_domain = recruiter_email.split("@")[-1].lower().strip()
    if email_domain in FREE_EMAIL_DOMAINS:
        findings.append((
            "RECRUITER_EMAIL_MISMATCH",
            email_domain,
            "The recruiter is using a free personal email service rather than an official company email address.",
        ))
    return findings


def run_rule_based_analysis(data, active_signals_by_code, thresholds=None):
    """
    data: dict with the submitted opportunity fields (see AnalyzerForm)
    active_signals_by_code: dict[code] -> RiskSignal (only currently active ones)
    thresholds: optional dict with 'low_max' / 'medium_max'

    Returns a dict:
      {
        "score": int 0-100,
        "level": "Low" | "Medium" | "High",
        "findings": [ {code, name, category, observed_value, explanation, weight}, ... ],
        "positive_indicators": [str, ...],
        "missing_information": [str, ...],
      }
    """
    thresholds = thresholds or {"low_max": 29, "medium_max": 59}
    text = _text_corpus(data)
    findings = []

    def add_finding(code, observed_value, fallback_explanation):
        signal = active_signals_by_code.get(code)
        if signal is None:
            return  # signal disabled by admin - skip silently
        findings.append({
            "code": code,
            "name": signal.signal_name,
            "category": signal.category,
            "observed_value": observed_value,
            "explanation": signal.description or fallback_explanation,
            "weight": signal.default_weight,
        })

    # Payment signals
    for code, patterns in PAYMENT_KEYWORDS.items():
        match = _find_keyword_match(text, patterns)
        if match:
            add_finding(code, match, "Potential payment-related warning sign detected in the submitted text.")

    # Communication signals
    for code, patterns in COMMUNICATION_KEYWORDS.items():
        match = _find_keyword_match(text, patterns)
        if match:
            add_finding(code, match, "Potential communication-related warning sign detected in the submitted text.")

    # Company signals
    if not (data.get("company_name") or "").strip():
        add_finding("MISSING_COMPANY_INFO", "not provided", "No company name was provided.")

    if not (data.get("recruiter_email") or "").strip() and not (data.get("recruiter_name") or "").strip():
        add_finding("INCOMPLETE_CONTACT_INFO", "not provided", "No recruiter contact details were provided.")

    for code, observed, explanation in _check_recruiter_email(data.get("recruiter_email"), data.get("company_url")):
        add_finding(code, observed, explanation)

    # URL signals
    for code, observed, explanation in _check_url_signals(data.get("company_url")):
        add_finding(code, observed, explanation)
    for code, observed, explanation in _check_company_url_match(data.get("company_name"), data.get("company_url")):
        add_finding(code, observed, explanation)

    # Deduplicate by code (keep first occurrence)
    seen = set()
    unique_findings = []
    for f in findings:
        if f["code"] in seen:
            continue
        seen.add(f["code"])
        unique_findings.append(f)

    raw_score = sum(f["weight"] for f in unique_findings)
    score = max(0, min(100, raw_score))

    if score <= thresholds["low_max"]:
        level = "Low"
    elif score <= thresholds["medium_max"]:
        level = "Medium"
    else:
        level = "High"

    # Positive / reassuring indicators
    positive_indicators = []
    if data.get("company_url") and not any(f["code"].startswith(("INVALID_URL", "URL_SHORTENER", "SUSPICIOUS_URL", "COMPANY_URL")) for f in unique_findings):
        positive_indicators.append("A company website URL was provided and did not trigger any URL-based warning signs.")
    if data.get("recruiter_email") and "RECRUITER_EMAIL_MISMATCH" not in seen:
        positive_indicators.append("The recruiter's email domain does not match common free/personal email providers.")
    if not any(f["category"] == "payment" for f in unique_findings):
        positive_indicators.append("No payment, deposit, or fee requests were detected in the submitted information.")
    if not any(f["category"] == "communication" for f in unique_findings):
        positive_indicators.append("No urgent, threatening, or manipulative language patterns were detected.")

    # Missing information prompts
    missing_information = []
    if not (data.get("company_url") or "").strip():
        missing_information.append("Company website or opportunity URL")
    if not (data.get("recruiter_email") or "").strip():
        missing_information.append("Recruiter email address")
    if not (data.get("stipend_or_salary") or "").strip():
        missing_information.append("Salary or stipend details")
    if not (data.get("description") or "").strip():
        missing_information.append("Detailed job/internship description")

    return {
        "score": score,
        "level": level,
        "findings": unique_findings,
        "positive_indicators": positive_indicators,
        "missing_information": missing_information,
    }


def default_verification_checklist():
    """Static checklist template shown for every new analysis."""
    return [
        "Is the company website available and does it look legitimate?",
        "Does the recruiter use an appropriate company email address?",
        "Is the opportunity listed on the company's official careers page?",
        "Are any payment requests being made at any stage?",
        "Are the job responsibilities clearly and specifically explained?",
        "Is the stipend or salary information realistic and transparent?",
        "Are the interview and selection steps clearly described?",
    ]

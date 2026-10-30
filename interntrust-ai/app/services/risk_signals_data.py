"""Default risk signal catalogue used to seed the risk_signals table.

Weights are initial design choices (documented in README.md) and can be
edited by an administrator at runtime through the Admin Panel; the values
here are only the starting defaults.
"""

DEFAULT_RISK_SIGNALS = [
    # --- Payment-related signals ---
    {
        "signal_code": "REGISTRATION_FEE",
        "signal_name": "Registration fee requested",
        "category": "payment",
        "description": "The opportunity asks the applicant to pay a registration fee.",
        "default_weight": 25,
    },
    {
        "signal_code": "TRAINING_FEE",
        "signal_name": "Training / course fee requested",
        "category": "payment",
        "description": "Applicant is asked to pay for mandatory training or a course before starting.",
        "default_weight": 22,
    },
    {
        "signal_code": "SECURITY_DEPOSIT",
        "signal_name": "Security deposit requested",
        "category": "payment",
        "description": "A refundable or non-refundable deposit is requested before onboarding.",
        "default_weight": 22,
    },
    {
        "signal_code": "INTERVIEW_FEE",
        "signal_name": "Interview fee requested",
        "category": "payment",
        "description": "Applicant is asked to pay simply to be interviewed or shortlisted.",
        "default_weight": 24,
    },
    {
        "signal_code": "PAY_BEFORE_JOINING",
        "signal_name": "Payment required before joining",
        "category": "payment",
        "description": "Any payment is requested before an official offer or joining date.",
        "default_weight": 20,
    },
    {
        "signal_code": "SUSPICIOUS_PAYMENT_CHANNEL",
        "signal_name": "Suspicious payment channel",
        "category": "payment",
        "description": "Payment is requested via personal UPI/wallet/crypto instead of an official channel.",
        "default_weight": 18,
    },
    # --- Communication signals ---
    {
        "signal_code": "URGENCY_PRESSURE",
        "signal_name": "Excessive urgency or pressure",
        "category": "communication",
        "description": "Message pressures the applicant to act or pay immediately, often with a countdown.",
        "default_weight": 12,
    },
    {
        "signal_code": "UNREALISTIC_PROMISES",
        "signal_name": "Unrealistic promises",
        "category": "communication",
        "description": "Promises of unusually high pay for minimal work or guaranteed placement.",
        "default_weight": 14,
    },
    {
        "signal_code": "THREATENING_LANGUAGE",
        "signal_name": "Threatening or manipulative language",
        "category": "communication",
        "description": "Message uses threats, guilt, or manipulation to force a decision.",
        "default_weight": 16,
    },
    {
        "signal_code": "SENSITIVE_INFO_REQUEST",
        "signal_name": "Unjustified request for sensitive information",
        "category": "communication",
        "description": "Requests bank details, ID numbers, or passwords without a clear, verifiable reason.",
        "default_weight": 20,
    },
    # --- Company & recruiter signals ---
    {
        "signal_code": "MISSING_COMPANY_INFO",
        "signal_name": "Missing company information",
        "category": "company",
        "description": "No verifiable company name, address, or official presence is provided.",
        "default_weight": 12,
    },
    {
        "signal_code": "RECRUITER_EMAIL_MISMATCH",
        "signal_name": "Recruiter email domain mismatch",
        "category": "company",
        "description": "Recruiter uses a free/personal email domain instead of a company domain.",
        "default_weight": 14,
    },
    {
        "signal_code": "INCOMPLETE_CONTACT_INFO",
        "signal_name": "Incomplete contact information",
        "category": "company",
        "description": "No phone number, address, or way to verify the recruiter independently.",
        "default_weight": 8,
    },
    # --- URL signals ---
    {
        "signal_code": "INVALID_URL",
        "signal_name": "Invalid or malformed URL",
        "category": "url",
        "description": "The provided company/opportunity URL is not a valid, well-formed web address.",
        "default_weight": 10,
    },
    {
        "signal_code": "URL_SHORTENER",
        "signal_name": "URL shortener used",
        "category": "url",
        "description": "A link-shortening service is used, hiding the true destination domain.",
        "default_weight": 12,
    },
    {
        "signal_code": "SUSPICIOUS_URL_PATTERN",
        "signal_name": "Suspicious URL pattern",
        "category": "url",
        "description": "URL contains patterns often used to imitate legitimate brands (e.g. odd subdomains).",
        "default_weight": 14,
    },
    {
        "signal_code": "COMPANY_URL_MISMATCH",
        "signal_name": "Company name / URL mismatch",
        "category": "url",
        "description": "The domain name does not resemble the stated company name at all.",
        "default_weight": 10,
    },
]

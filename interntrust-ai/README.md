# InternTrust AI

**AI-Powered Internship and Job Opportunity Risk Assessment and Verification Platform for Students**

> *"Don't Trust Every Internship. Verify It."*

InternTrust AI is a full-stack Flask web application that helps students assess the potential
risk of internship and job opportunities they receive through WhatsApp, LinkedIn, email, and
other channels — using a transparent, explainable rule-based risk engine, with an optional
AI-assisted explanation layer.

**InternTrust AI never declares an opportunity "fraudulent."** It reports risk indicators
(Low / Medium / High) and explains every signal, so the final judgment always stays with the
student.

---

## 1. Tech Stack

| Layer          | Technology |
|----------------|------------|
| Frontend       | HTML5, CSS3, Bootstrap 5, Bootstrap Icons, Chart.js, Jinja2 |
| Backend        | Python 3.11+, Flask, Flask Blueprints, Flask-Login, Flask-WTF, Flask-Limiter |
| Database       | SQLite (dev) + SQLAlchemy ORM, portable to MySQL/PostgreSQL |
| AI (optional)  | Anthropic Claude API (Messages endpoint) — app fully works without it |
| PDF Reports    | ReportLab |
| Security       | Werkzeug password hashing, CSRF protection, rate limiting, role-based access |

---

## 2. Project Structure

```
interntrust-ai/
├── app/
│   ├── __init__.py            # Application factory
│   ├── config.py              # Environment-driven configuration
│   ├── extensions.py          # Flask extension instances
│   ├── models.py              # SQLAlchemy models
│   ├── cli.py                 # `flask init-db`, `flask create-admin`
│   ├── utils.py                # student_required / admin_required decorators
│   ├── blueprints/
│   │   ├── main/               # Public website (landing, about, how it works...)
│   │   ├── auth/               # Student + Admin authentication
│   │   ├── student/             # Dashboard, Analyzer, History, Profile
│   │   └── admin/               # Admin Panel
│   ├── services/
│   │   ├── risk_engine.py       # Rule-based risk assessment engine
│   │   ├── risk_signals_data.py # Default risk signal catalogue
│   │   ├── ai_engine.py          # Optional Anthropic AI explanation layer
│   │   ├── file_processing.py   # Safe upload handling + text extraction
│   │   └── pdf_report.py         # ReportLab PDF generation
│   ├── templates/                # Jinja2 templates (matte-black/purple theme)
│   └── static/                    # CSS + JS
├── instance/
│   ├── interntrust.db            # SQLite database (created on init)
│   ├── uploads/                    # Uploaded documents (randomized filenames)
│   └── reports/                    # Generated PDF reports
├── tests/                           # Pytest test suite
├── run.py                            # Local development entry point
├── wsgi.py                            # Production WSGI entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Local Setup (Development)

```bash
# 1. Clone / unzip the project, then enter the folder
cd interntrust-ai

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and set a real SECRET_KEY. Leave ANTHROPIC_API_KEY empty to run
# in rule-based-only mode, or add a key to enable AI-assisted explanations.

# 5. Initialize the database and seed default risk signals
flask init-db

# 6. Create your first administrator account (safe, interactive, no
#    passwords in shell history or source code)
flask create-admin

# 7. Run the development server
python run.py
# Visit http://127.0.0.1:5000
```

Student signup is open at `/auth/signup`. Administrators log in separately at
`/auth/admin-login` — students can never reach the admin panel, and the reverse.

### Running the tests

```bash
pytest
```

---

## 4. Production Deployment Notes

- Set `FLASK_ENV=production`, a strong random `SECRET_KEY`, and `SESSION_COOKIE_SECURE=true`
  (requires HTTPS).
- Swap `DATABASE_URL` for a MySQL/PostgreSQL connection string — the SQLAlchemy models make no
  SQLite-specific assumptions.
- Run behind Gunicorn: `gunicorn wsgi:app --workers 3 --bind 0.0.0.0:8000`
- Put Gunicorn behind Nginx (or similar) for TLS termination and static file caching.
- Point `RATELIMIT_STORAGE_URI` at Redis instead of `memory://` for multi-worker rate limiting.
- Never commit `.env` — only `.env.example` ships in the repository.

---

## 5. Database Design (ER Overview)

```
users (1) ───< (many) analyses (1) ───< (many) analysis_signals >─── (many) risk_signals
                    │
                    ├──< (1) reports
                    └──< (many) checklist_progress

admins (1) ───< (many) admin_activity_logs
```

**Key tables:**

- **users** — student accounts (`full_name`, `email`, `password_hash`, `role`, `is_active_account`)
- **admins** — administrator accounts, in a *separate table* from `users` so a student record can
  never be escalated into an admin by mistake
- **analyses** — one row per submitted opportunity, including the computed `risk_score`,
  `risk_level`, and `analysis_source` (`rule_based` or `ai_assisted`)
- **risk_signals** — the configurable catalogue of detectable signals (code, name, category,
  description, default weight, active/inactive) — editable by admins at `/admin/risk-signals`
- **analysis_signals** — the specific signals actually detected for one analysis, with the
  observed value, explanation, and score contribution
- **reports** — metadata for generated PDF reports (one per analysis)
- **checklist_progress** — per-analysis verification checklist item status
- **admin_activity_logs** — audit trail of administrative actions (deactivations, signal edits, etc.)

All foreign keys use `ON DELETE CASCADE` where a child record has no meaning without its parent
(e.g. deleting an analysis removes its signals, report, and checklist items).

---

## 6. Scoring Methodology

1. The rule-based engine (`app/services/risk_engine.py`) scans the submitted title, description,
   recruiter message, and any extracted document text for keyword/pattern matches across four
   signal categories: **payment**, **communication**, **company**, and **URL**.
2. Each *active* matched signal contributes its configured `default_weight` (0–100) to the score.
   Weights are additive and clamped to a 0–100 final score.
3. Thresholds (configurable in `app/config.py`):
   - **0–29 → Low Risk**
   - **30–59 → Medium Risk**
   - **60–100 → High Risk**
4. These thresholds and every signal's weight/active-state are **initial design choices** —
   administrators can adjust them at runtime from the Admin Panel without a code change.
5. The engine also reports **positive indicators** (e.g. no payment requests detected) and
   **missing information** (e.g. no company URL provided) so results are never one-sided.
6. If an Anthropic API key is configured, an optional AI layer summarizes the opportunity and
   rewrites signal explanations in plain language — it **never** changes the score, and all
   submitted text is treated as untrusted data (not instructions) when sent to the model, to
   guard against prompt injection from a malicious job posting or uploaded document.
7. If the AI layer is unavailable or fails for any reason, the app automatically falls back to
   the rule-based explanation and the result is clearly labeled `Rule-Based Engine` — the
   pipeline never crashes and never fabricates an AI response.

---

## 7. Security Measures Implemented

- Passwords hashed with Werkzeug's `generate_password_hash` (salted, never stored/shown in plain text)
- CSRF protection on every state-changing form via Flask-WTF
- Server-side validation on every form field (WTForms validators)
- Secure, `HttpOnly`, `SameSite=Lax` session cookies (`Secure` flag enabled in production)
- Role-based access control: `student_required` / `admin_required` decorators enforce
  authorization on the server for every protected route — never only hidden frontend links
- SQL injection protection via SQLAlchemy's parameterized queries (no raw SQL string building)
- File upload validation: extension allow-list, 5MB size limit, randomized stored filenames
  (UUID-based) to prevent path traversal or overwrite attacks, defensive text extraction that
  never crashes on a corrupted/empty/unsupported document
- Rate limiting on login and analysis-submission endpoints (Flask-Limiter)
- Ownership checks before returning any analysis or PDF report (`_get_owned_analysis_or_404`)
- Admin activity logging for deactivations, signal changes, and sensitive views
- No hardcoded secrets or API keys anywhere in source code — all via environment variables
- `.env` is git-ignored; only `.env.example` (with no real secrets) ships in the repo

**Honest limitation:** this is an academic project. It has not undergone a professional
penetration test or formal security audit, and additional hardening (e.g. Content-Security-Policy
headers, structured audit logging, background malware scanning of uploads) would be needed before
handling real users' sensitive data in production.

---

## 8. Known Limitations / Future Work

- The rule-based engine uses keyword/pattern matching, which can produce false positives or
  false negatives — it is a decision-support tool, not a definitive verdict.
- URL signal checks are pattern-based only; the app never fetches or accesses external URLs.
- The AI layer requires an Anthropic API key and network access; without it, the platform
  degrades gracefully to rule-based-only mode.
- Password reset via email is not implemented in this version (`password_reset_tokens` table is
  a natural next addition).

---

## 9. Academic / Portfolio Notes

This project was built to demonstrate a complete, working full-stack application: relational
database design, an original explainable scoring algorithm, secure authentication with two
distinct account types, file handling, PDF generation, an optional real AI integration, and a
polished, responsive UI — suitable for a college submission, viva demonstration, GitHub
portfolio, and internship interview discussion.

# NEXA SOC — Security Operations Portal

A defensive, rule-based **log-analysis and alerting portal** built with Python, Flask, SQLite and pytest. Upload or paste server logs, and NEXA SOC parses them, flags suspicious activity, lets analysts write investigation notes, and exports CSV / PDF incident reports.

> Educational project. Detections are *indicators for investigation*, not proof of compromise.

![Dashboard](docs/screenshots/04-dashboard-analyzed.png)

---

## Table of contents
- [Features](#features)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Secret key setup (required)](#secret-key-setup-required)
- [Using the app](#using-the-app)
- [Detection rules](#detection-rules)
- [Supported log formats](#supported-log-formats)
- [Security design](#security-design)
- [Running tests](#running-tests)
- [Production notes](#production-notes)

---

## Features
- **Accounts** — register / sign in with username or email (local accounts, not Google OAuth). Passwords hashed with PBKDF2-SHA256 (210,000 iterations).
- **Data isolation** — every analyst sees only their own events, alerts, notifications, audit history and reports.
- **Log ingestion** — upload `.log` / `.txt` files or paste log lines directly (2 MB limit).
- **Detection engine** — 17 rules covering brute force, injection attacks, scanners, enumeration and more.
- **Event explorer** — browse every parsed event with a full-record and raw-log view.
- **Alert investigation** — per-alert analyst write-ups stored in SQLite and included in the PDF report.
- **Notification center** — in-portal notifications with severity labels; critical-alert banner with 7-second polling.
- **Reports** — CSV export and a multi-section PDF incident report (severity summary, detection register, evidence, analyst notes).
- **Audit trail** — login success/failure and key actions are logged per account.
- **Rate limiting** — on sign-in, registration, upload and analysis, plus app-wide limits.

## Screenshots

### Sign in & registration
| Sign in | Create account |
|---|---|
| ![Login](docs/screenshots/01-login.png) | ![Register](docs/screenshots/02-register.png) |

Registration enforces a strong password (12+ characters with upper, lower, number and symbol) and offers a locally generated random password suggestion.

### Dashboard
Empty workspace on first login, ready for a log upload:

![Empty dashboard](docs/screenshots/03-dashboard-empty.png)

After analyzing `sample_logs/security_sample.log` — totals, latest detections and portal notifications:

![Dashboard after analysis](docs/screenshots/04-dashboard-analyzed.png)

### Security alerts
Filter by severity and open any alert with **Inspect**:

![Alerts](docs/screenshots/05-alerts.png)

### Alert investigation
Review the evidence and save your analyst write-up (included in the PDF report):

![Alert detail](docs/screenshots/06-alert-detail.png)

### Event explorer
| Event list | Event detail |
|---|---|
| ![Events](docs/screenshots/07-events.png) | ![Event detail](docs/screenshots/08-event-detail.png) |

### Notification center & audit log
| Notifications | My activity (audit) |
|---|---|
| ![Notifications](docs/screenshots/09-notifications.png) | ![Audit](docs/screenshots/10-audit.png) |

## Tech stack
| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3 |
| Database | SQLite |
| Rate limiting | Flask-Limiter |
| PDF reports | ReportLab |
| Config | python-dotenv |
| Frontend | Jinja2 templates, custom CSS |
| Tests | pytest |

## Project structure
```
NEXA_SOC/
├── run.py                  # App entry point
├── requirements.txt
├── .env.example            # Template for your secret key
├── sample_logs/
│   └── security_sample.log # Demo log with attack patterns
├── app/
│   ├── __init__.py         # App factory, rate limiter, security headers
│   ├── config.py           # Settings, loads NEXA_SOC_SECRET_KEY
│   ├── database.py         # SQLite schema + admin seed
│   ├── parser.py           # Log line parsing (auth, web, generic)
│   ├── detectors.py        # Detection rules + correlation
│   ├── security.py         # Password hashing and validation
│   ├── routes.py           # All web routes, CSV/PDF export
│   ├── templates/          # HTML pages
│   └── static/style.css
├── tests/                  # pytest suite
└── docs/screenshots/       # Images used in this README
```

## Quick start

### Windows (PowerShell)
```powershell
cd NEXA_SOC
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Kali Linux / WSL / Linux / macOS
```bash
cd NEXA_SOC
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```
If the venv module is missing on Kali/Debian: `sudo apt install python3-venv`.

Then complete the secret-key setup below and run:
```bash
python run.py
```
Open **http://127.0.0.1:5000**.

**Demo account:** `admin` / `ChangeMe123!` — change this for anything beyond a local demo. Or choose **Create an account** to register a separate user.

## Secret key setup (required)
The app **refuses to start** if `NEXA_SOC_SECRET_KEY` is empty or missing.

1. Copy the template (skip if `.env` already exists):
   ```bash
   cp .env.example .env
   ```
2. Generate a random key:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Paste the 64-character value into `.env`:
   ```env
   NEXA_SOC_SECRET_KEY=paste_your_generated_value_here
   NEXA_SOC_HTTPS=0
   ```
4. Set `NEXA_SOC_HTTPS=1` only when the app is served over HTTPS (enables secure cookies).

`.env` is listed in `.gitignore`. **Never commit or share it.**

## Using the app
1. Sign in (or register) and land on the **Overview** dashboard.
2. Upload `sample_logs/security_sample.log` or paste log lines into the text box.
3. Open **Security alerts** and click **Inspect** on a finding.
4. Write your investigation notes and save them.
5. Browse **Event explorer** → *Details* for the complete record and raw line.
6. Check **Notifications** for severity-labelled findings.
7. Download the **PDF report** or **CSV** from the sidebar.

## Detection rules
| Category | Rules |
|---|---|
| Authentication | `AUTH_BRUTE_FORCE`, `AUTH_SUCCESS_AFTER_FAILURES`, `SENSITIVE_ACCOUNT_FAILURE`, `PRIVILEGED_LOGIN` |
| Web attacks | `SQL_INJECTION`, `CROSS_SITE_SCRIPTING`, `PATH_TRAVERSAL`, `COMMAND_INJECTION`, `FILE_INCLUSION` |
| Recon / scanning | `SCANNER_INDICATOR`, `SENSITIVE_PATH_PROBE`, `RESOURCE_ENUMERATION`, `HTTP_ERROR_ENUMERATION`, `AUTOMATED_CLIENT` |
| Behavior | `HTTP_REQUEST_BURST`, `UNCOMMON_HTTP_METHOD`, `ACCESS_DENIED` |

Severities: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, each with a confidence percentage.

## Supported log formats
```text
# SSH / authentication
2026-11-02 10:01:02 sshd[101]: Failed password for alice from 10.0.0.50
2026-11-02 10:01:20 sshd[107]: Accepted password for alice from 10.0.0.50

# Web request  (timestamp  ip  METHOD  path  status  ua=...)
2026-11-02 10:03:12 10.0.0.23 GET /.env 404 ua=sqlmap/1.8
```
Lines that match neither pattern are stored as generic events.

## Security design
- PBKDF2-SHA256 password hashing with per-user salt and constant-time comparison
- Strong-password policy on registration
- Session cookies: `HttpOnly`, `SameSite=Lax`, `Secure` when HTTPS is enabled
- Response headers: CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`
- Upload restricted to `.log` / `.txt`, 2 MB maximum
- Per-account data isolation and an audit log

## Running tests
```bash
pytest -v
```

## Production notes
This is a learning project. Before exposing it to the internet:
- Use a production WSGI server (e.g. Gunicorn) and disable `debug=True` in `run.py`
- Replace the in-memory rate-limit store with Redis
- Add CSRF protection, HTTPS, MFA, backups and retention policies
- Change or remove the default `admin` demo account
- Use a long, random `NEXA_SOC_SECRET_KEY`

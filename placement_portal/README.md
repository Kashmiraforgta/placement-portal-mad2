# Placement Portal Application (PPA)

MAD 2 project — Jan 2026 term.  
Stack: **Flask** (API) · **Vue 3** (CDN, no build step) · **Bootstrap 5** · **SQLite** · **Redis** · **Celery** · **ChartJS**

---

## Folder structure

```
placement_portal/
├── run.py                  # Flask dev server entry point
├── celery_worker.py        # Celery worker + beat schedule entry point
├── config.py               # All config (db, redis, celery, mail, uploads)
├── seed_data.py            # One-off demo data seeder
├── requirements.txt
├── instance/               # SQLite DB + uploaded resumes/exports (gitignored)
└── app/
    ├── __init__.py         # App factory, extension wiring, admin seeding
    ├── extensions.py       # db, login_manager, cache, celery singletons
    ├── models.py           # User, Company, Student, Drive, Application
    ├── tasks.py            # 3 Celery jobs (reminders, monthly report, CSV export)
    ├── routes/
    │   ├── pages.py        # Serves the Vue SPA shell
    │   ├── auth.py         # register / login / logout / me
    │   ├── admin.py        # dashboard, approvals, search, blacklist, chart stats
    │   ├── company.py      # profile, drives, applicant management, interviews
    │   ├── student.py      # profile, resume, browse/apply, export, offer letter
    │   └── utils.py        # role_required decorator
    ├── templates/
    │   └── index.html      # Single HTML shell — all Vue templates live here
    └── static/
        ├── css/style.css
        └── js/
            ├── api.js      # Tiny fetch wrapper (cookie-based sessions)
            └── app.js      # All Vue components + root instance
```

---

## First-time setup

```bash
# Windows (cmd / PowerShell)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Redis** must be running before starting the app or Celery:
- Windows: use [Memurai](https://www.memurai.com/) or run `wsl redis-server`
- Or: `docker run -d -p 6379:6379 redis`

---

## Running the app

Open **3 terminals**, all with the venv activated, from the `placement_portal/` directory:

```bash
# Terminal 1 — Flask dev server
python run.py                          # → http://localhost:5000

# Terminal 2 — Celery worker (processes background jobs)
celery -A celery_worker.celery worker --loglevel=info

# Terminal 3 — Celery beat (fires scheduled jobs on time)
celery -A celery_worker.celery beat --loglevel=info
```

On first run the app auto-creates `instance/placement.db` and seeds the admin:

```
email:    admin@portal.com
password: admin123
```

Override via env vars: `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

To load demo data (companies, students, drives, applications):
```bash
python seed_data.py
```

---

## Email configuration

Emails fall back to `print()` (console) if `MAIL_SERVER` is not set.  
To enable real email (e.g. Gmail), set these env vars:

```bash
set MAIL_SERVER=smtp.gmail.com
set MAIL_PORT=587
set MAIL_USERNAME=your@gmail.com
set MAIL_PASSWORD=your_app_password
set MAIL_SENDER=your@gmail.com
```

---

## Roles & flow

| Role | Key Actions |
|---|---|
| **Admin** | Approve/reject companies & drives · View all applications · Search users · Blacklist accounts · View placement charts |
| **Company** | Register · Edit profile · Create drives (post-approval) · Manage applicants · Schedule interviews |
| **Student** | Register · Edit profile · Upload resume · Browse & apply to drives · View application status & interview dates · Export history as CSV · Download offer letter (if selected) |

---

## Background jobs (`app/tasks.py`)

| Job | Type | Schedule | What it does |
|---|---|---|---|
| `send_daily_reminders` | Scheduled | Daily 08:00 | Emails students with active applications for drives closing within 24h |
| `generate_monthly_report` | Scheduled | 1st of month 06:00 | Sends HTML placement summary report to admin via email |
| `export_applications_csv` | Async (user-triggered) | On demand | Exports student's application history to CSV, emails them when ready |

---

## API endpoints summary

### Auth (`/api/auth`)
| Method | Route | Description |
|---|---|---|
| POST | `/register` | Student or company self-registration |
| POST | `/login` | Login (all roles) |
| POST | `/logout` | Logout |
| GET | `/me` | Current user info |

### Admin (`/api/admin`)
| Method | Route | Description |
|---|---|---|
| GET | `/dashboard` | Stats: students, companies, drives, applications, selected |
| GET | `/stats/charts` | ChartJS data: per-drive counts, status breakdown, company breakdown |
| GET | `/companies` | List companies (optional `?status=` filter) |
| PATCH | `/companies/<id>/status` | Approve or reject a company |
| GET | `/drives` | List drives (optional `?status=` filter) |
| PATCH | `/drives/<id>/status` | Approve, close, or reopen a drive |
| GET | `/applications` | All applications (optional `?status=` filter) |
| GET | `/students` | All students |
| GET | `/search?q=` | Search students (name/ID/email) and companies |
| PATCH | `/users/<id>/blacklist` | Toggle blacklist on a user |

### Company (`/api/company`)
| Method | Route | Description |
|---|---|---|
| GET/PUT | `/profile` | View or update company profile |
| GET/POST | `/drives` | List drives or create a new one |
| GET | `/drives/<id>/applications` | Applicants for a specific drive |
| PATCH | `/applications/<id>/status` | Shortlist, select, or reject an applicant |
| PATCH | `/applications/<id>/interview` | Schedule an interview date |

### Student (`/api/student`)
| Method | Route | Description |
|---|---|---|
| GET/PUT | `/profile` | View or update student profile |
| POST | `/resume` | Upload resume (PDF/DOC/DOCX, max 5MB) |
| GET | `/drives` | Browse approved drives (optional `?branch=` filter) |
| POST | `/drives/<id>/apply` | Apply to a drive (with eligibility check) |
| GET | `/applications` | My application history |
| POST | `/applications/export` | Trigger async CSV export |
| GET | `/tasks/<task_id>` | Poll export job status |
| GET | `/applications/<id>/offer-letter` | Download offer letter (selected only) |

---

## Database schema (ER summary)

```
User (id, email, password_hash, role, is_active_flag)
  ├── Company (user_id FK, name, hr_contact, website, approval_status)
  │     └── Drive (company_id FK, job_title, job_description, eligibility_*, deadline, status)
  │           └── Application (student_id FK, drive_id FK, status, applied_at, interview_date)
  └── Student (user_id FK, name, branch, cgpa, year, resume_path)
              └── Application (same, other side)
```

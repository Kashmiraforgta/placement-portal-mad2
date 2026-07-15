"""
Run the Celery worker (in one terminal):
    celery -A celery_worker.celery worker --loglevel=info

Run the beat scheduler (in another terminal):
    celery -A celery_worker.celery beat --loglevel=info

Emails are sent to MailHog by default.
Download MailHog: https://github.com/mailhog/MailHog/releases
Run it:           MailHog.exe         (Windows)
View emails:      http://localhost:8025
"""
import os
from app import create_app
from app.extensions import celery
import app.tasks  # noqa: F401  (registers the tasks with Celery)
from celery.schedules import crontab

flask_app = create_app()

# ---------------------------------------------------------------------------
# Beat schedule
# ---------------------------------------------------------------------------
# DEMO_MODE: set CELERY_DEMO_MODE=true to fire the daily reminder every
# 1 minute instead of once a day — useful for showing it works in a viva.
# Default (production): daily at 08:00, monthly report on 1st of month.
# ---------------------------------------------------------------------------
DEMO_MODE = os.environ.get("CELERY_DEMO_MODE", "false").lower() == "true"

if DEMO_MODE:
    daily_reminder_schedule = 60  # every 60 seconds — for live demo
    print("[celery] DEMO MODE: daily reminders fire every 60 seconds")
else:
    daily_reminder_schedule = crontab(hour=8, minute=0)  # 08:00 every day

celery.conf.beat_schedule = {
    "daily-reminders": {
        "task": "tasks.send_daily_reminders",
        "schedule": daily_reminder_schedule,
    },
    "monthly-activity-report": {
        "task": "tasks.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),  # 1st of month 06:00
    },
}

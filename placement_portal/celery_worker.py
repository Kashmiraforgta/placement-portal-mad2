"""
Run with:
    celery -A celery_worker.celery worker --loglevel=info
Run the beat scheduler (for the two scheduled jobs) with:
    celery -A celery_worker.celery beat --loglevel=info
"""
from app import create_app
from app.extensions import celery
import app.tasks  # noqa: F401  (registers the tasks with celery)
from celery.schedules import crontab

flask_app = create_app()

# Periodic schedule: daily reminders every morning, monthly report on the 1st.
celery.conf.beat_schedule = {
    "daily-reminders": {
        "task": "tasks.send_daily_reminders",
        "schedule": crontab(hour=8, minute=0),  # every day 08:00
    },
    "monthly-activity-report": {
        "task": "tasks.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),  # 1st of month, 06:00
    },
}

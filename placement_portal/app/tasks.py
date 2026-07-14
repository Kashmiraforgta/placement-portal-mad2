import csv
import io
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.extensions import celery, db
from app.models import Student, Drive, Application, User


# ---------------------------------------------------------------------------
# Email helper — uses Flask app config for SMTP settings
# ---------------------------------------------------------------------------
def _send_email(to_addr: str, subject: str, html_body: str):
    """
    Send an email via SMTP. Reads config from the Flask app context.
    Set MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD in config.py.
    Falls back to printing if MAIL_SERVER is not configured.
    """
    from flask import current_app
    mail_server = current_app.config.get("MAIL_SERVER")
    mail_port = current_app.config.get("MAIL_PORT", 587)
    mail_username = current_app.config.get("MAIL_USERNAME")
    mail_password = current_app.config.get("MAIL_PASSWORD")
    mail_sender = current_app.config.get("MAIL_SENDER", mail_username)

    if not mail_server or not mail_username:
        # Fallback: just log — useful during development
        print(f"[email] To: {to_addr} | Subject: {subject}\n{html_body}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_sender
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo()
            server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, to_addr, msg.as_string())
    except Exception as e:
        print(f"[email error] Failed to send to {to_addr}: {e}")


# ---------------------------------------------------------------------------
# a. Scheduled job — daily reminders to students who have APPLIED for drives
#    with deadlines tomorrow, reminding them of their scheduled appointment.
# ---------------------------------------------------------------------------
@celery.task(name="tasks.send_daily_reminders")
def send_daily_reminders():
    """
    Remind students who have an APPLIED/SHORTLISTED application for a drive
    whose deadline falls within the next 24 hours.
    """
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)

    # Get drives closing soon
    upcoming_drives = Drive.query.filter(
        Drive.status == "approved",
        Drive.application_deadline.between(now, tomorrow),
    ).all()

    sent = 0
    for drive in upcoming_drives:
        for application in drive.applications:
            if application.status not in ("applied", "shortlisted"):
                continue
            student = application.student
            if not student or not student.user:
                continue
            subject = f"Reminder: '{drive.job_title}' at {drive.company.name} closes soon"
            body = f"""
            <p>Hi {student.name},</p>
            <p>This is a reminder that you have applied for <strong>{drive.job_title}</strong>
            at <strong>{drive.company.name}</strong>.</p>
            <p>The application deadline is <strong>{drive.application_deadline.strftime('%Y-%m-%d %H:%M UTC')}</strong>.</p>
            <p>Current status: <strong>{application.status}</strong></p>
            <p>Good luck!</p>
            """
            _send_email(student.user.email, subject, body)
            sent += 1

    return {"reminders_sent": sent}


# ---------------------------------------------------------------------------
# b. Scheduled job — monthly placement activity report for admin
# ---------------------------------------------------------------------------
@celery.task(name="tasks.generate_monthly_report")
def generate_monthly_report():
    from flask import current_app

    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    drives_this_month = Drive.query.filter(Drive.created_at >= first_of_month).all()
    applications_this_month = Application.query.filter(Application.applied_at >= first_of_month).count()
    selected_this_month = Application.query.filter(
        Application.applied_at >= first_of_month,
        Application.status == "selected",
    ).count()

    # Build per-drive stats rows
    drive_rows = ""
    for d in drives_this_month:
        total_apps = len(d.applications)
        selected = sum(1 for a in d.applications if a.status == "selected")
        drive_rows += f"""
        <tr>
          <td>{d.job_title}</td>
          <td>{d.company.name if d.company else '—'}</td>
          <td>{d.status}</td>
          <td>{total_apps}</td>
          <td>{selected}</td>
        </tr>"""

    html = f"""
    <html><body>
    <h2>Monthly Placement Report — {first_of_month.strftime('%B %Y')}</h2>
    <h3>Summary</h3>
    <ul>
      <li>Drives created this month: <strong>{len(drives_this_month)}</strong></li>
      <li>Total applications received: <strong>{applications_this_month}</strong></li>
      <li>Students selected: <strong>{selected_this_month}</strong></li>
    </ul>
    <h3>Drive Details</h3>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead>
        <tr><th>Job Title</th><th>Company</th><th>Status</th><th>Applicants</th><th>Selected</th></tr>
      </thead>
      <tbody>{drive_rows}</tbody>
    </table>
    </body></html>
    """

    admin_user = User.query.filter_by(role="admin").first()
    if admin_user:
        _send_email(
            admin_user.email,
            f"Monthly Placement Report — {first_of_month.strftime('%B %Y')}",
            html,
        )

    return {
        "drives": len(drives_this_month),
        "applications": applications_this_month,
        "selected": selected_this_month,
    }


# ---------------------------------------------------------------------------
# c. User-triggered async job — export a student's applications as CSV
#    Emails the student when done (also saves file locally for download).
# ---------------------------------------------------------------------------
@celery.task(name="tasks.export_applications_csv")
def export_applications_csv(student_id):
    from flask import current_app

    student = Student.query.get(student_id)
    if not student:
        return {"error": "student not found"}

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Student ID", "Company Name", "Drive Title", "Application Status", "Date Applied", "Interview Date"])
    for app in student.applications:
        writer.writerow([
            student.id,
            app.drive.company.name if app.drive and app.drive.company else "",
            app.drive.job_title if app.drive else "",
            app.status,
            app.applied_at.strftime("%Y-%m-%d") if app.applied_at else "",
            app.interview_date.strftime("%Y-%m-%d %H:%M") if app.interview_date else "",
        ])

    export_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"applications_student_{student_id}_{datetime.utcnow():%Y%m%d%H%M%S}.csv"
    filepath = os.path.join(export_dir, filename)
    with open(filepath, "w", newline="") as f:
        f.write(buffer.getvalue())

    # Alert the student via email
    if student.user:
        _send_email(
            student.user.email,
            "Your application export is ready",
            f"""
            <p>Hi {student.name},</p>
            <p>Your application history CSV export is ready.</p>
            <p>File: <strong>{filename}</strong></p>
            <p>You can download it from your dashboard.</p>
            """,
        )

    return {"file": filename}

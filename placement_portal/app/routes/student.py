import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db, cache, celery
from app.models import Student, Drive, Application
from app.routes.utils import role_required

student_bp = Blueprint("student", __name__)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _current_student():
    return Student.query.filter_by(user_id=current_user.id).first()


@student_bp.route("/profile", methods=["GET", "PUT"])
@login_required
@role_required("student")
def profile():
    student = _current_student()
    if request.method == "GET":
        return jsonify(student.to_dict())

    data = request.get_json(force=True)
    student.name = data.get("name", student.name)
    student.branch = data.get("branch", student.branch)
    student.cgpa = data.get("cgpa", student.cgpa)
    student.year = data.get("year", student.year)
    db.session.commit()
    return jsonify(student.to_dict())


@student_bp.route("/resume", methods=["POST"])
@login_required
@role_required("student")
def upload_resume():
    student = _current_student()
    file = request.files.get("resume")
    if not file:
        return jsonify({"error": "no file provided"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "only PDF, DOC, DOCX files are allowed"}), 400

    filename = secure_filename(f"student_{student.id}_{file.filename}")
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    student.resume_path = filename
    db.session.commit()
    return jsonify(student.to_dict())


@student_bp.route("/drives")
@login_required
@role_required("student")
@cache.cached(timeout=30, query_string=True)
def browse_drives():
    q = Drive.query.filter_by(status="approved")
    branch = request.args.get("branch")
    if branch:
        q = q.filter(Drive.eligibility_branch.ilike(f"%{branch}%"))
    return jsonify([d.to_dict() for d in q.all()])


@student_bp.route("/drives/<int:drive_id>/apply", methods=["POST"])
@login_required
@role_required("student")
def apply_to_drive(drive_id):
    student = _current_student()
    drive = Drive.query.get_or_404(drive_id)

    if drive.status != "approved":
        return jsonify({"error": "drive not open for applications"}), 400
    if Application.query.filter_by(student_id=student.id, drive_id=drive_id).first():
        return jsonify({"error": "already applied to this drive"}), 409

    # Eligibility validation
    if drive.eligibility_cgpa and student.cgpa and student.cgpa < drive.eligibility_cgpa:
        return jsonify({"error": f"CGPA {student.cgpa} is below the required {drive.eligibility_cgpa}"}), 400
    if drive.eligibility_year and student.year and student.year != drive.eligibility_year:
        return jsonify({"error": f"Year {student.year} does not match required year {drive.eligibility_year}"}), 400
    if drive.eligibility_branch and student.branch:
        allowed = [b.strip().lower() for b in drive.eligibility_branch.split(",")]
        if student.branch.lower() not in allowed:
            return jsonify({"error": f"Your branch '{student.branch}' is not eligible for this drive"}), 400

    application = Application(student_id=student.id, drive_id=drive_id)
    db.session.add(application)
    db.session.commit()
    return jsonify(application.to_dict()), 201


@student_bp.route("/applications")
@login_required
@role_required("student")
def my_applications():
    student = _current_student()
    return jsonify([a.to_dict() for a in student.applications])


@student_bp.route("/applications/export", methods=["POST"])
@login_required
@role_required("student")
def export_applications():
    """Kicks off an async Celery job; poll /tasks/<task_id> for status."""
    from app.tasks import export_applications_csv
    student = _current_student()
    task = export_applications_csv.delay(student.id)
    return jsonify({"message": "export started", "task_id": task.id}), 202


@student_bp.route("/tasks/<task_id>")
@login_required
@role_required("student")
def task_status(task_id):
    """Poll this endpoint to check if an async export job is done."""
    result = celery.AsyncResult(task_id)
    if result.state == "PENDING":
        return jsonify({"state": "pending", "ready": False})
    if result.state == "SUCCESS":
        return jsonify({"state": "success", "ready": True, "result": result.result})
    if result.state == "FAILURE":
        return jsonify({"state": "failure", "ready": False, "error": str(result.result)}), 500
    return jsonify({"state": result.state, "ready": False})


@student_bp.route("/applications/<int:application_id>/offer-letter")
@login_required
@role_required("student")
def offer_letter(application_id):
    """Generate a dummy offer letter for a selected application."""
    student = _current_student()
    application = Application.query.get_or_404(application_id)

    if application.student_id != student.id:
        return jsonify({"error": "forbidden"}), 403
    if application.status != "selected":
        return jsonify({"error": "offer letter only available for selected applications"}), 400

    drive = application.drive
    company = drive.company if drive else None

    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; border: 1px solid #ccc; }}
        h1 {{ color: #2c3e50; }} h2 {{ color: #555; }}
        .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 15px; margin-bottom: 25px; }}
        .field {{ margin: 8px 0; }} .label {{ font-weight: bold; color: #333; }}
        .footer {{ margin-top: 40px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 0.85em; color: #777; }}
        .stamp {{ color: green; font-size: 1.5em; font-weight: bold; border: 3px solid green; display: inline-block; padding: 5px 15px; transform: rotate(-5deg); margin-top: 20px; }}
      </style>
    </head>
    <body>
      <div class="header">
        <h1>{company.name if company else 'Company'}</h1>
        <h2>Offer Letter</h2>
        <p>Date: {application.applied_at.strftime('%B %d, %Y') if application.applied_at else 'N/A'}</p>
      </div>
      <p>Dear <strong>{student.name}</strong>,</p>
      <p>We are pleased to inform you that you have been selected for the following position:</p>
      <div class="field"><span class="label">Position:</span> {drive.job_title if drive else 'N/A'}</div>
      <div class="field"><span class="label">Company:</span> {company.name if company else 'N/A'}</div>
      <div class="field"><span class="label">HR Contact:</span> {company.hr_contact if company else 'N/A'}</div>
      <div class="field"><span class="label">Website:</span> {company.website if company and company.website else 'N/A'}</div>
      <div class="field"><span class="label">Candidate:</span> {student.name}</div>
      <div class="field"><span class="label">Branch:</span> {student.branch or 'N/A'}</div>
      <div class="field"><span class="label">CGPA:</span> {student.cgpa or 'N/A'}</div>
      <p style="margin-top: 20px;">
        This offer is contingent upon the successful completion of background verification and all joining formalities.
        Please report to HR within 7 working days to confirm acceptance of this offer.
      </p>
      <p>We look forward to welcoming you to our team!</p>
      <br>
      <p>Sincerely,<br><strong>HR Department</strong><br>{company.name if company else 'Company'}</p>
      <div class="stamp">SELECTED ✓</div>
      <div class="footer">
        This is a system-generated offer letter from the Placement Portal. Application ID: {application.id}
      </div>
    </body>
    </html>
    """
    from flask import Response
    return Response(html, mimetype="text/html")

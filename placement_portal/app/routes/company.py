from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Company, Drive, Application
from app.routes.utils import role_required

company_bp = Blueprint("company", __name__)


def _current_company():
    return Company.query.filter_by(user_id=current_user.id).first()


@company_bp.route("/profile", methods=["GET", "PUT"])
@login_required
@role_required("company")
def profile():
    company = _current_company()
    if request.method == "GET":
        return jsonify(company.to_dict())

    data = request.get_json(force=True)
    company.name = data.get("name", company.name)
    company.hr_contact = data.get("hr_contact", company.hr_contact)
    company.website = data.get("website", company.website)
    db.session.commit()
    return jsonify(company.to_dict())


@company_bp.route("/drives", methods=["GET", "POST"])
@login_required
@role_required("company")
def drives():
    company = _current_company()

    if request.method == "GET":
        return jsonify([d.to_dict() for d in company.drives])

    if company.approval_status != "approved":
        return jsonify({"error": "company not yet approved by admin"}), 403

    data = request.get_json(force=True)
    deadline = data.get("application_deadline")

    # Vue's v-model.number sends "" when a number field is left blank,
    # not null — sanitize before passing to Float/Integer columns.
    cgpa = data.get("eligibility_cgpa")
    cgpa = float(cgpa) if cgpa not in (None, "") else 0.0

    year = data.get("eligibility_year")
    year = int(year) if year not in (None, "") else None

    drive = Drive(
        company_id=company.id,
        job_title=data.get("job_title"),
        job_description=data.get("job_description"),
        eligibility_branch=data.get("eligibility_branch") or None,
        eligibility_cgpa=cgpa,
        eligibility_year=year,
        application_deadline=datetime.fromisoformat(deadline) if deadline else None,
        status="pending",  # goes live only after admin approval
    )
    db.session.add(drive)
    db.session.commit()
    return jsonify(drive.to_dict()), 201


@company_bp.route("/drives/<int:drive_id>/applications")
@login_required
@role_required("company")
def drive_applications(drive_id):
    company = _current_company()
    drive = Drive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    return jsonify([a.to_dict() for a in drive.applications])


@company_bp.route("/applications/<int:application_id>/status", methods=["PATCH"])
@login_required
@role_required("company")
def update_application_status(application_id):
    company = _current_company()
    application = Application.query.get_or_404(application_id)
    if application.drive.company_id != company.id:
        return jsonify({"error": "forbidden"}), 403

    new_status = request.get_json(force=True).get("status")
    if new_status not in ("shortlisted", "selected", "rejected"):
        return jsonify({"error": "invalid status"}), 400

    application.status = new_status
    db.session.commit()
    return jsonify(application.to_dict())


@company_bp.route("/applications/<int:application_id>/interview", methods=["PATCH"])
@login_required
@role_required("company")
def schedule_interview(application_id):
    """Set an interview date for a shortlisted applicant."""
    company = _current_company()
    application = Application.query.get_or_404(application_id)
    if application.drive.company_id != company.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(force=True)
    interview_date_str = data.get("interview_date")
    if not interview_date_str:
        return jsonify({"error": "interview_date is required"}), 400

    try:
        application.interview_date = datetime.fromisoformat(interview_date_str)
    except ValueError:
        return jsonify({"error": "invalid date format, use ISO 8601"}), 400

    # Automatically mark as shortlisted if still in 'applied' state
    if application.status == "applied":
        application.status = "shortlisted"

    db.session.commit()
    return jsonify(application.to_dict())

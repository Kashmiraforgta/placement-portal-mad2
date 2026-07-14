from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.extensions import db, cache
from app.models import User, Company, Student, Drive, Application
from app.routes.utils import role_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
@cache.cached(timeout=30)
def dashboard():
    total_drives = Drive.query.count()
    total_selected = Application.query.filter_by(status="selected").count()
    return jsonify({
        "total_students": Student.query.count(),
        "total_companies": Company.query.count(),
        "total_drives": total_drives,
        "total_applications": Application.query.count(),
        "total_selected": total_selected,
    })


@admin_bp.route("/companies")
@login_required
@role_required("admin")
def list_companies():
    status = request.args.get("status")
    q = Company.query
    if status:
        q = q.filter_by(approval_status=status)
    return jsonify([c.to_dict() for c in q.all()])


@admin_bp.route("/companies/<int:company_id>/status", methods=["PATCH"])
@login_required
@role_required("admin")
def update_company_status(company_id):
    data = request.get_json(force=True)
    new_status = data.get("status")
    if new_status not in ("approved", "rejected"):
        return jsonify({"error": "status must be approved or rejected"}), 400

    company = Company.query.get_or_404(company_id)
    company.approval_status = new_status
    db.session.commit()
    cache.delete_memoized(dashboard)
    return jsonify(company.to_dict())


@admin_bp.route("/drives")
@login_required
@role_required("admin")
def list_drives():
    status = request.args.get("status")
    q = Drive.query
    if status:
        q = q.filter_by(status=status)
    return jsonify([d.to_dict() for d in q.all()])


@admin_bp.route("/drives/<int:drive_id>/status", methods=["PATCH"])
@login_required
@role_required("admin")
def update_drive_status(drive_id):
    data = request.get_json(force=True)
    new_status = data.get("status")
    if new_status not in ("approved", "closed", "pending"):
        return jsonify({"error": "invalid status"}), 400

    drive = Drive.query.get_or_404(drive_id)
    drive.status = new_status
    db.session.commit()
    return jsonify(drive.to_dict())


@admin_bp.route("/applications")
@login_required
@role_required("admin")
def list_all_applications():
    """View all student applications across all drives."""
    status = request.args.get("status")
    q = Application.query
    if status:
        q = q.filter_by(status=status)
    return jsonify([a.to_dict() for a in q.order_by(Application.applied_at.desc()).all()])


@admin_bp.route("/search")
@login_required
@role_required("admin")
def search():
    """Search students (by name, ID, email/contact) and companies (by name)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"students": [], "companies": []})

    like = f"%{q}%"

    # Try numeric match for student ID
    student_by_id = []
    try:
        sid = int(q)
        found = Student.query.get(sid)
        if found:
            student_by_id = [found]
    except ValueError:
        pass

    students_by_name = Student.query.filter(Student.name.ilike(like)).all()

    # Search by email (contact info) — join through User
    students_by_email = (
        Student.query
        .join(User, Student.user_id == User.id)
        .filter(User.email.ilike(like))
        .all()
    )

    # Deduplicate
    seen_ids = set()
    students = []
    for s in student_by_id + students_by_name + students_by_email:
        if s.id not in seen_ids:
            seen_ids.add(s.id)
            students.append(s)

    companies = Company.query.filter(Company.name.ilike(like)).all()

    return jsonify({
        "students": [s.to_dict() for s in students],
        "companies": [c.to_dict() for c in companies],
    })


@admin_bp.route("/students")
@login_required
@role_required("admin")
def list_students():
    """List all students (used by admin management view)."""
    return jsonify([s.to_dict() for s in Student.query.all()])


@admin_bp.route("/users/<int:user_id>/blacklist", methods=["PATCH"])
@login_required
@role_required("admin")
def toggle_blacklist(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        return jsonify({"error": "cannot blacklist admin"}), 400
    user.is_active_flag = not user.is_active_flag
    db.session.commit()
    return jsonify(user.to_dict() | {"is_active": user.is_active_flag})


@admin_bp.route("/stats/charts")
@login_required
@role_required("admin")
@cache.cached(timeout=60)
def chart_stats():
    """Return data for ChartJS charts on the admin dashboard."""
    from app.models import Application

    # Applications per drive (top 10 by count)
    drives = Drive.query.filter(Drive.status.in_(["approved", "closed"])).all()
    drives_sorted = sorted(drives, key=lambda d: len(d.applications), reverse=True)[:10]
    per_drive = {
        "labels": [d.job_title[:20] + ("…" if len(d.job_title) > 20 else "") for d in drives_sorted],
        "data":   [len(d.applications) for d in drives_sorted],
    }

    # Application status breakdown
    statuses = ["applied", "shortlisted", "selected", "rejected"]
    status_counts = {s: Application.query.filter_by(status=s).count() for s in statuses}
    status_chart = {
        "labels": [s.capitalize() for s in statuses],
        "data":   [status_counts[s] for s in statuses],
    }

    # Companies by approval status
    company_statuses = ["pending", "approved", "rejected"]
    from app.models import Company
    company_counts = {s: Company.query.filter_by(approval_status=s).count() for s in company_statuses}
    company_chart = {
        "labels": [s.capitalize() for s in company_statuses],
        "data":   [company_counts[s] for s in company_statuses],
    }

    return jsonify({
        "per_drive": per_drive,
        "status_breakdown": status_chart,
        "company_breakdown": company_chart,
    })

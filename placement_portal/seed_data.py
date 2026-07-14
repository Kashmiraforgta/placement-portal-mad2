"""
One-off script to populate the database with realistic demo data so you can
actually click around the UI without manually registering everything by hand.

Run once, with the venv activated, from the project root:
    python seed_data.py

Safe to re-run — it checks for existing emails before inserting anything.
"""
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Company, Student, Drive, Application

app = create_app()

with app.app_context():

    def get_or_create_user(email, password, role):
        user = User.query.filter_by(email=email).first()
        if user:
            return user, False
        user = User(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        return user, True

    # ---------------- Companies ----------------
    companies_data = [
        {"email": "hr@techcorp.com", "name": "TechCorp Solutions", "hr_contact": "9876543210",
         "website": "techcorp.com", "status": "approved"},
        {"email": "careers@innoware.com", "name": "InnoWare Systems", "hr_contact": "9876500000",
         "website": "innoware.com", "status": "approved"},
        {"email": "jobs@newstartup.io", "name": "NewStartup.io", "hr_contact": "9123456789",
         "website": "newstartup.io", "status": "pending"},
    ]

    companies = {}
    for c in companies_data:
        user, created = get_or_create_user(c["email"], "password123", "company")
        company = Company.query.filter_by(user_id=user.id).first()
        if not company:
            company = Company(user_id=user.id, name=c["name"], hr_contact=c["hr_contact"],
                               website=c["website"], approval_status=c["status"])
            db.session.add(company)
            db.session.flush()
        companies[c["email"]] = company

    # ---------------- Students ----------------
    students_data = [
        {"email": "rahul@student.com", "name": "Rahul Sharma", "branch": "Computer Science", "cgpa": 8.5, "year": 4},
        {"email": "priya@student.com", "name": "Priya Nair", "branch": "Electronics", "cgpa": 9.1, "year": 4},
        {"email": "amit@student.com", "name": "Amit Verma", "branch": "Mechanical", "cgpa": 7.2, "year": 3},
    ]

    students = {}
    for s in students_data:
        user, created = get_or_create_user(s["email"], "password123", "student")
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            student = Student(user_id=user.id, name=s["name"], branch=s["branch"],
                               cgpa=s["cgpa"], year=s["year"])
            db.session.add(student)
            db.session.flush()
        students[s["email"]] = student

    db.session.commit()

    # ---------------- Drives ----------------
    drives_data = [
        {"company": "hr@techcorp.com", "title": "Software Development Engineer",
         "desc": "Full-stack role working on our core product.", "branch": "Computer Science",
         "cgpa": 7.5, "year": 4, "status": "approved"},
        {"company": "hr@techcorp.com", "title": "Data Analyst Intern",
         "desc": "6-month internship analyzing product usage data.", "branch": "Computer Science,Electronics",
         "cgpa": 7.0, "year": 3, "status": "approved"},
        {"company": "careers@innoware.com", "title": "Embedded Systems Engineer",
         "desc": "Work on firmware for IoT devices.", "branch": "Electronics",
         "cgpa": 8.0, "year": 4, "status": "approved"},
        {"company": "careers@innoware.com", "title": "QA Engineer",
         "desc": "Manual + automation testing role.", "branch": "Computer Science,Mechanical",
         "cgpa": 6.5, "year": 4, "status": "pending"},  # awaiting admin approval
    ]

    drives = []
    for d in drives_data:
        company = companies[d["company"]]
        existing = Drive.query.filter_by(company_id=company.id, job_title=d["title"]).first()
        if existing:
            drives.append(existing)
            continue
        drive = Drive(
            company_id=company.id,
            job_title=d["title"],
            job_description=d["desc"],
            eligibility_branch=d["branch"],
            eligibility_cgpa=d["cgpa"],
            eligibility_year=d["year"],
            application_deadline=datetime.utcnow() + timedelta(days=14),
            status=d["status"],
        )
        db.session.add(drive)
        db.session.flush()
        drives.append(drive)

    db.session.commit()

    # ---------------- Applications ----------------
    approved_drives = [d for d in drives if d.status == "approved"]
    applications_data = [
        {"student": "rahul@student.com", "drive": approved_drives[0], "status": "shortlisted"},
        {"student": "rahul@student.com", "drive": approved_drives[1], "status": "applied"},
        {"student": "priya@student.com", "drive": approved_drives[2], "status": "selected"},
        {"student": "amit@student.com", "drive": approved_drives[0], "status": "rejected"},
    ]

    for a in applications_data:
        student = students[a["student"]]
        exists = Application.query.filter_by(student_id=student.id, drive_id=a["drive"].id).first()
        if exists:
            continue
        db.session.add(Application(student_id=student.id, drive_id=a["drive"].id, status=a["status"]))

    db.session.commit()

    print("Demo data seeded.\n")
    print("Login credentials (all passwords: password123):")
    print("  Companies :", ", ".join(companies.keys()))
    print("  Students  :", ", ".join(students.keys()))
    print("  Admin     : admin@portal.com / admin123")

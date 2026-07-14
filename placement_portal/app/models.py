from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """
    Unified user model for all three roles: admin / company / student.
    Role-specific extra fields live in Company / Student below.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' | 'company' | 'student'
    is_active_flag = db.Column(db.Boolean, default=True)  # used for blacklist/deactivate
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship("Company", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_active(self):
        return self.is_active_flag

    def to_dict(self):
        return {"id": self.id, "email": self.email, "role": self.role}


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    hr_contact = db.Column(db.String(120))
    website = db.Column(db.String(200))
    approval_status = db.Column(db.String(20), default="pending")  # pending | approved | rejected

    user = db.relationship("User", back_populates="company")
    drives = db.relationship("Drive", back_populates="company", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hr_contact": self.hr_contact,
            "website": self.website,
            "approval_status": self.approval_status,
        }


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(80))
    cgpa = db.Column(db.Float)
    year = db.Column(db.Integer)
    resume_path = db.Column(db.String(255))

    user = db.relationship("User", back_populates="student")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "branch": self.branch,
            "cgpa": self.cgpa,
            "year": self.year,
            "resume_path": self.resume_path,
            "email": self.user.email if self.user else None,
        }


class Drive(db.Model):
    __tablename__ = "drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text)
    eligibility_branch = db.Column(db.String(120))   # comma separated
    eligibility_cgpa = db.Column(db.Float, default=0)
    eligibility_year = db.Column(db.Integer)
    application_deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="pending")  # pending | approved | closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship("Company", back_populates="drives")
    applications = db.relationship("Application", back_populates="drive", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "job_title": self.job_title,
            "job_description": self.job_description,
            "eligibility_branch": self.eligibility_branch,
            "eligibility_cgpa": self.eligibility_cgpa,
            "eligibility_year": self.eligibility_year,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "status": self.status,
            "applicant_count": len(self.applications),
        }


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey("drives.id"), nullable=False)
    status = db.Column(db.String(20), default="applied")  # applied | shortlisted | selected | rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    interview_date = db.Column(db.DateTime, nullable=True)  # set by company when scheduling interview

    student = db.relationship("Student", back_populates="applications")
    drive = db.relationship("Drive", back_populates="applications")

    __table_args__ = (
        db.UniqueConstraint("student_id", "drive_id", name="uq_student_drive"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_branch": self.student.branch if self.student else None,
            "drive_id": self.drive_id,
            "job_title": self.drive.job_title if self.drive else None,
            "company_name": self.drive.company.name if self.drive and self.drive.company else None,
            "status": self.status,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "interview_date": self.interview_date.isoformat() if self.interview_date else None,
        }

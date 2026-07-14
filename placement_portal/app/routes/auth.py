from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Company, Student

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login_page")
def login_page():
    # Flask-Login redirects here (unauthenticated) — the SPA shell handles
    # showing the login form itself, so we just render the same shell.
    from flask import render_template
    return render_template("index.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Only students and companies can self-register. Admin is never created here."""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role")
    name = data.get("name", "").strip()

    if role not in ("student", "company"):
        return jsonify({"error": "role must be 'student' or 'company'"}), 400
    if not email or not password or not name:
        return jsonify({"error": "email, password and name are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id before commit

    if role == "student":
        profile = Student(user_id=user.id, name=name)
    else:
        profile = Company(user_id=user.id, name=name)
    db.session.add(profile)
    db.session.commit()

    return jsonify({"message": "registered", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401
    if not user.is_active_flag:
        return jsonify({"error": "account deactivated"}), 403

    login_user(user)
    return jsonify({"message": "logged in", "user": user.to_dict()})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "logged out"})


@auth_bp.route("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"user": None})
    return jsonify({"user": current_user.to_dict()})

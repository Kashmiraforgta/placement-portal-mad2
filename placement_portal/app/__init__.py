import os
from flask import Flask
from config import Config
from app.extensions import db, login_manager, cache, celery


def create_app(config_class=Config):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instance_path = os.path.join(project_root, "instance")

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        instance_path=instance_path,
    )
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # --- init extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    cache.init_app(app)
    make_celery(app)

    # --- register blueprints ---
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.company import company_bp
    from app.routes.student import student_bp
    from app.routes.pages import pages_bp

    app.register_blueprint(pages_bp)               # serves the Vue SPA shell
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(company_bp, url_prefix="/api/company")
    app.register_blueprint(student_bp, url_prefix="/api/student")

    with app.app_context():
        db.create_all()
        auto_migrate()
        seed_admin(app)

    return app


def seed_admin(app):
    """Create the single pre-existing admin if it doesn't already exist.
    No admin registration route exists anywhere in the app on purpose."""
    from app.models import User

    existing = User.query.filter_by(role="admin").first()
    if not existing:
        admin = User(email=app.config["ADMIN_EMAIL"], role="admin")
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        print(f"[seed] Admin created -> {app.config['ADMIN_EMAIL']} / {app.config['ADMIN_PASSWORD']}")


def auto_migrate():
    """
    Lightweight schema migration: add any columns that exist in SQLAlchemy
    models but are missing from the actual SQLite tables.
    Uses raw PRAGMA — no Flask-Migrate needed.
    """
    from sqlalchemy import text

    # Map: table_name -> [(column_name, column_definition), ...]
    migrations = {
        "applications": [
            ("interview_date", "DATETIME"),
        ],
        "students": [
            ("resume_path", "VARCHAR(255)"),
        ],
        "drives": [
            ("eligibility_year", "INTEGER"),
            ("eligibility_cgpa", "FLOAT"),
        ],
    }

    with db.engine.connect() as conn:
        for table, columns in migrations.items():
            # Get existing columns for this table
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            existing = {row[1] for row in result.fetchall()}  # row[1] = column name

            for col_name, col_type in columns:
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                    ))
                    print(f"[migrate] Added column {table}.{col_name}")

        conn.commit()


def make_celery(app):
    """Bind the shared Celery instance to this Flask app's config so tasks
    run inside an application context (needed for db access in tasks.py)."""
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

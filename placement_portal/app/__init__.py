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

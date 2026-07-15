import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # --- Database (SQLite, created programmatically via SQLAlchemy) ---
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "placement.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Redis cache ---
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 60

    # --- Celery (Redis as broker + result backend) ---
    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/1")

    # --- Uploads (resumes + exports) ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    # --- Default admin (seeded on first run) ---
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@portal.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # --- Email (SMTP) ---
    # Default: MailHog (local dev mail catcher, no auth needed).
    # Download: https://github.com/mailhog/MailHog/releases
    # Run:      MailHog.exe           (Windows)
    # Web UI:   http://localhost:8025
    #
    # For real email (e.g. Gmail), override with env vars:
    #   MAIL_SERVER=smtp.gmail.com  MAIL_PORT=587
    #   MAIL_USERNAME=you@gmail.com  MAIL_PASSWORD=app_password
    #   MAIL_USE_TLS=true
    MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "localhost")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 1025))       # MailHog SMTP port
    MAIL_USE_TLS  = os.environ.get("MAIL_USE_TLS",  "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", None)        # not needed for MailHog
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", None)        # not needed for MailHog
    MAIL_SENDER   = os.environ.get("MAIL_SENDER",   "noreply@placement.portal")

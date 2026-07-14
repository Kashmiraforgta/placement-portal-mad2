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
    # To enable real email: set these env vars before running the app.
    # Example for Gmail:
    #   MAIL_SERVER=smtp.gmail.com  MAIL_PORT=587
    #   MAIL_USERNAME=your@gmail.com  MAIL_PASSWORD=your_app_password
    #   MAIL_SENDER=your@gmail.com
    # If MAIL_SERVER is not set, emails fall back to console printing (dev mode).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")          # e.g. smtp.gmail.com
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SENDER = os.environ.get("MAIL_SENDER", os.environ.get("MAIL_USERNAME"))

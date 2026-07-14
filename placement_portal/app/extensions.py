from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from celery import Celery

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()

# Celery instance is created here but bound to the Flask app's config
# inside create_app() (see app/__init__.py -> make_celery()).
celery = Celery(__name__)

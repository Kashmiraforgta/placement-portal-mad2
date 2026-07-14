from functools import wraps
from flask import jsonify
from flask_login import current_user


def role_required(*roles):
    """Usage: @role_required('admin') or @role_required('admin', 'company')"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "login required"}), 401
            if current_user.role not in roles:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

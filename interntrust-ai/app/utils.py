from functools import wraps
from flask import abort
from flask_login import current_user

from app.models import User, Admin


def student_required(view_func):
    """Ensures the logged-in account is a student, never an administrator."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, User):
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    """Ensures the logged-in account is an administrator, never a student."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped

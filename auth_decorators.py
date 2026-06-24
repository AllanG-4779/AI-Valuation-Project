"""
auth_decorators.py

A role-based access decorator that sits on top of Flask-Login's
@login_required. @login_required only checks "is someone logged in" —
it doesn't know about roles. This adds that layer.

Usage:
    @app.route("/admin")
    @login_required
    @role_required("admin")
    def admin_dashboard():
        ...

    @app.route("/sale")
    @login_required
    @role_required("owner")
    def sale():
        ...

Order matters: @login_required must be ABOVE @role_required (closer to
the route), so login is checked first, then role.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.role not in allowed_roles:
                # 403 Forbidden — they ARE logged in, just not allowed here.
                # This is different from @login_required's redirect-to-login
                # behavior, which is for users who aren't logged in at all.
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
from functools import wraps
from flask import session, redirect

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect("/admin_login")
        return f(*args, **kwargs)
    return decorated

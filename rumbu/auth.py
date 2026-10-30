"""Web accounts. Farmers never log in: their phone number is their account.

Roles:
  buyer    - aggregators, mills, traders. Sign up themselves.
  partner  - government, NGOs, insurers. Read-only insights. Created by admin.
  admin    - RUMBU team / agronomists. Full operations console.
"""
from functools import wraps

from flask import abort, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

ROLES = ("buyer", "partner", "admin")
HOME = {"buyer": "buyer_portal", "partner": "partner_insights", "admin": "admin_console"}


def create_user(email, password, name, role, org="", phone=""):
    email = email.strip().lower()
    if role not in ROLES:
        raise ValueError("Unknown role")
    if db.q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
        raise ValueError("An account with this email already exists.")
    return db.ex(
        "INSERT INTO users (email, name, org, phone, role, password_hash, created_at) VALUES (?,?,?,?,?,?,?)",
        (email, name.strip(), org.strip(), db.normalize_phone(phone), role,
         generate_password_hash(password), db.now()),
    )


def authenticate(email, password):
    u = db.q("SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),), one=True)
    if u and check_password_hash(u["password_hash"], password or ""):
        return u
    return None


def load_user():
    uid = session.get("uid")
    g.user = db.q("SELECT id, email, name, org, phone, role FROM users WHERE id=?", (uid,), one=True) if uid else None


def login(user):
    session.clear()
    session["uid"] = user["id"]
    session.permanent = True


def logout():
    session.clear()


def home_for(user):
    return url_for(HOME[user["role"]])


def require(*roles):
    """Allow only logged-in users with one of these roles (admin can open everything)."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not g.get("user"):
                return redirect(url_for("login", next=request.path))
            if g.user["role"] not in roles and g.user["role"] != "admin":
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco

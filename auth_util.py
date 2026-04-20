"""Signed auth tokens and request guards."""

from __future__ import annotations

import os
from functools import wraps

from flask import jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("FLASK_SECRET_KEY", "").strip()
    if not secret or secret == "change-me":
        raise RuntimeError("Set a strong FLASK_SECRET_KEY in .env (not the placeholder).")
    return URLSafeTimedSerializer(secret, salt="dura-capital-auth-v1")


def create_auth_token(email: str) -> str:
    normalized = email.strip().lower()
    return _serializer().dumps({"email": normalized})


def verify_auth_token(token: str, max_age: int | None = None) -> str | None:
    if max_age is None:
        max_age = int(os.environ.get("TOKEN_MAX_AGE_SECONDS", str(8 * 3600)))
    try:
        ser = _serializer()
    except RuntimeError:
        return None
    try:
        data = ser.loads(token, max_age=max_age)
        return (data.get("email") or "").strip().lower() or None
    except (BadSignature, SignatureExpired):
        return None


def allowed_login_email() -> str:
    return os.environ.get("ALLOWED_LOGIN_EMAIL", "").strip().lower()


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        token = auth[7:].strip()
        try:
            email = verify_auth_token(token)
        except Exception:
            email = None
        allowed = allowed_login_email()
        if not allowed:
            return jsonify({"error": "server misconfiguration"}), 500
        if not email or email != allowed:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)

    return wrapped

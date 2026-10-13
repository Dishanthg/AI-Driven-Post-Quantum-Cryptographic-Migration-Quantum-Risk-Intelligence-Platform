"""Authentication (JWT) and RBAC primitives.

Threat-model note (docs/architecture/adr / Section 51 of the design doc):
This module is the ONLY place allowed to mint or verify auth tokens, and every
state-changing API route depends on `require_role` below. An LLM-generated
explanation string can never itself carry authorization - only a verified
JWT bound to a human/service account can.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

# Calling `bcrypt` directly rather than through passlib's CryptContext: passlib
# 1.7.x's bcrypt backend self-test is incompatible with bcrypt>=4.1 (it probes
# a removed internal attribute), a known unresolved upstream issue. bcrypt
# itself remains a vetted, actively maintained password-hashing library
# (Rule 6), so this is a thinner wrapper over the same primitive, not a
# hand-rolled one.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"
ALL_ROLES = (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# A fixed bcrypt hash of an unreachable password, hashed once at import time.
# `login()` runs verify_password against this whenever the username lookup
# itself fails, so an unknown-username request pays the same bcrypt cost as a
# known-username/wrong-password one - otherwise the two cases are
# distinguishable by response time alone (bcrypt is deliberately slow;
# skipping it entirely on a missing user is a measurable, exploitable signal
# for username enumeration).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"unreachable-dummy-password", bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    expire = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


class CurrentUser:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    username = payload.get("sub")
    role = payload.get("role")
    if not username or role not in ALL_ROLES:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return CurrentUser(username=username, role=role)


def require_role(*allowed: Iterable[str]):
    allowed_roles = set(allowed)

    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this action")
        return user

    return _dep

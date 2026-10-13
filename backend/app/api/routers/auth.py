# NOTE: no `from __future__ import annotations` in this file, unlike the rest of
# the codebase - slowapi's @limiter.limit decorator wraps the route function, and
# combined with postponed (string) annotations, FastAPI's signature introspection
# fails to resolve OAuth2PasswordRequestForm's own forward references (surfaces as
# `TypeError: ForwardRef(...) is not a class` at app startup). Real, executed
# annotations avoid the issue; every annotation in this file is a plain runtime
# type FastAPI itself needs to resolve anyway, so nothing else changes.
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.rate_limit import AUTH_LIMIT, limiter
from app.core.security import _DUMMY_PASSWORD_HASH, create_access_token, verify_password
from app.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token")
@limiter.limit(AUTH_LIMIT)
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=form_data.username).one_or_none()
    # Always run bcrypt, even for a username that doesn't exist, so lookup
    # failure and wrong-password failure take the same time (see
    # security._DUMMY_PASSWORD_HASH).
    password_ok = verify_password(form_data.password, user.hashed_password if user else _DUMMY_PASSWORD_HASH)
    if user is None or not user.is_active or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token(subject=user.username, role=user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}

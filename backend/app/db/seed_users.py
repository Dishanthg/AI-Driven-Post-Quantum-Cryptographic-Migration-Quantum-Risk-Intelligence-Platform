"""Seeds three demo accounts (design doc Section 44 login page / Section 50
RBAC). LAB-ONLY default credentials - printed to stdout, never committed
anywhere, and only meant for exercising the demo locally (see
QS_SECRET_KEY / .env for the token-signing key, which must be overridden for
anything beyond local development).

Run via: python -m app.db.seed_users
"""
from __future__ import annotations

import secrets

from app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, hash_password
from app.db.models import User
from app.db.session import SessionLocal

DEMO_ACCOUNTS = [
    ("admin", "admin@quantumshield.lab", ROLE_ADMIN),
    ("analyst", "analyst@quantumshield.lab", ROLE_ANALYST),
    ("viewer", "viewer@quantumshield.lab", ROLE_VIEWER),
]


def main() -> None:
    db = SessionLocal()
    try:
        created = []
        for username, email, role in DEMO_ACCOUNTS:
            if db.query(User).filter_by(username=username).one_or_none():
                continue
            password = secrets.token_urlsafe(12)
            db.add(User(username=username, email=email, hashed_password=hash_password(password), role=role))
            created.append((username, password, role))
        db.commit()
        if not created:
            print("Demo accounts already exist; nothing to do.")
            return
        print("Created demo accounts (LAB ONLY - not for production use):")
        for username, password, role in created:
            print(f"  {username:10s} role={role:8s} password={password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

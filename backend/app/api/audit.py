"""Audit logging helper (design doc Section 50/14). Every state-changing
endpoint calls `record_audit` explicitly - not a blanket middleware - so each
call site records a meaningful before/after payload rather than a raw
request body dump.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def record_audit(db: Session, actor: str, action: str, target_type: str, target_id: str,
                  before: dict | None = None, after: dict | None = None) -> None:
    db.add(AuditLog(
        actor=actor, action=action, target_type=target_type, target_id=target_id,
        before_json=before or {}, after_json=after or {},
    ))
    db.commit()

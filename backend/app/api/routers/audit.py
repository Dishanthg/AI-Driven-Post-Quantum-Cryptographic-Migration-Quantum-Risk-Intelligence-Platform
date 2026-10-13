from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.api.schemas import AuditLogOut
from app.db.models import AuditLog

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(limit: int = 200, db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(min(limit, 1000)).all()

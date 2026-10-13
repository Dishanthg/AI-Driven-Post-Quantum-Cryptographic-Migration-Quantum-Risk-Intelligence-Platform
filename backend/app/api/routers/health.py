from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    model_ok = settings.model_registry_dir.exists() and any(settings.model_registry_dir.glob("*/*/model.joblib"))

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "risk_model_artifacts": "present" if model_ok else "missing",
        "app_name": settings.app_name,
        "environment": settings.environment,
    }

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_viewer
from app.api.schemas import ModelVersionOut
from app.db.models import ModelVersion

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("", response_model=list[ModelVersionOut])
def list_model_versions(db: Session = Depends(get_db), _=Depends(require_viewer)):
    return db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()

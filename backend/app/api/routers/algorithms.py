from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_viewer
from app.api.schemas import AlgorithmOut, ThreatEntryOut
from app.db.models import Algorithm
from app.quantum.threat_model import threat_for_algorithm

router = APIRouter(prefix="/api/v1/algorithms", tags=["algorithms"])


@router.get("", response_model=list[AlgorithmOut])
def list_algorithms(db: Session = Depends(get_db), _=Depends(require_viewer)):
    return db.query(Algorithm).order_by(Algorithm.family, Algorithm.name).all()


@router.get("/{algorithm_id}", response_model=AlgorithmOut)
def get_algorithm(algorithm_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    algo = db.get(Algorithm, algorithm_id)
    if algo is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    return algo


@router.get("/{algorithm_id}/threat", response_model=ThreatEntryOut)
def get_algorithm_threat(algorithm_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    algo = db.get(Algorithm, algorithm_id)
    if algo is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    entry = threat_for_algorithm(algorithm_id)
    return ThreatEntryOut(**entry.__dict__)

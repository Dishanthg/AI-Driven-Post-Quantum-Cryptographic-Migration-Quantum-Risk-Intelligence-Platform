from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import RiskAssessmentOut, RiskAssessRequest
from app.core.security import CurrentUser
from app.db.models import Asset, RiskAssessment
from app.risk.service import assess_all_assets, assess_asset

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("", response_model=list[RiskAssessmentOut])
def list_risk_assessments(asset_id: str | None = None, db: Session = Depends(get_db), _=Depends(require_viewer)):
    q = db.query(RiskAssessment)
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    return q.order_by(RiskAssessment.created_at.desc()).all()


@router.get("/asset/{asset_id}/latest", response_model=RiskAssessmentOut)
def latest_risk_for_asset(asset_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    r = (
        db.query(RiskAssessment)
        .filter_by(asset_id=asset_id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    if r is None:
        raise HTTPException(status_code=404, detail="No risk assessment for this asset yet")
    return r


@router.post("/asset/{asset_id}/assess", response_model=RiskAssessmentOut)
def assess_single_asset(asset_id: str, req: RiskAssessRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    assessment = assess_asset(db, asset, method=req.method)
    db.commit()
    record_audit(db, actor=user.username, action="risk_assess", target_type="asset", target_id=asset_id,
                 after={"risk_score": assessment.risk_score, "priority": assessment.priority, "method": req.method})
    return assessment


@router.post("/assess-all", response_model=list[RiskAssessmentOut])
def assess_all(req: RiskAssessRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    results = assess_all_assets(db, method=req.method)
    record_audit(db, actor=user.username, action="risk_assess_all", target_type="asset", target_id="*",
                 after={"count": len(results), "method": req.method})
    return results

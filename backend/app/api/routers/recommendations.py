from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import PQCRecommendationOut
from app.core.security import CurrentUser
from app.db.models import Asset, PQCRecommendation
from app.recommendations.engine import recommend_for_all_assets, recommend_for_asset

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=list[PQCRecommendationOut])
def list_recommendations(asset_id: str | None = None, strategy: str | None = None,
                          db: Session = Depends(get_db), _=Depends(require_viewer)):
    q = db.query(PQCRecommendation)
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    if strategy:
        q = q.filter_by(strategy=strategy)
    return q.order_by(PQCRecommendation.created_at.desc()).all()


@router.post("/asset/{asset_id}/recommend", response_model=PQCRecommendationOut)
def recommend_single(asset_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    rec = recommend_for_asset(db, asset)
    if rec is None:
        raise HTTPException(status_code=409, detail="No risk assessment exists for this asset yet; run /risk/asset/{id}/assess first")
    db.commit()
    record_audit(db, actor=user.username, action="recommend", target_type="asset", target_id=asset_id,
                 after={"strategy": rec.strategy, "target_algorithm_id": rec.target_algorithm_id})
    return rec


@router.post("/recommend-all", response_model=list[PQCRecommendationOut])
def recommend_all(db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    recs = recommend_for_all_assets(db)
    record_audit(db, actor=user.username, action="recommend_all", target_type="asset", target_id="*",
                 after={"count": len(recs)})
    return recs

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import AssetDetailOut, AssetOut, InventoryOverviewOut, ScanResultOut
from app.core.security import CurrentUser
from app.db.models import Asset, RiskAssessment
from app.discovery.scanner import scan_directory

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db), _=Depends(require_viewer)):
    return db.query(Asset).order_by(Asset.hostname).all()


@router.get("/overview", response_model=InventoryOverviewOut)
def inventory_overview(db: Session = Depends(get_db), _=Depends(require_viewer)):
    assets = db.query(Asset).all()
    from app.crypto import registry as algo_registry

    algo_dist: dict[str, int] = {}
    status_dist: dict[str, int] = {}
    legacy_pk = 0
    for a in assets:
        algo_dist[a.algorithm_id] = algo_dist.get(a.algorithm_id, 0) + 1
        status_dist[a.current_status] = status_dist.get(a.current_status, 0) + 1
        spec = algo_registry.get(a.algorithm_id)
        if spec.classification in ("classical_pk",):
            legacy_pk += 1

    priority_dist: dict[str, int] = {}
    high_risk, critical_risk = 0, 0
    for a in assets:
        latest = (
            db.query(RiskAssessment)
            .filter_by(asset_id=a.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        if latest:
            priority_dist[latest.priority] = priority_dist.get(latest.priority, 0) + 1
            if latest.priority == "high":
                high_risk += 1
            elif latest.priority == "critical":
                critical_risk += 1

    return InventoryOverviewOut(
        total_assets=len(assets),
        legacy_public_key_assets=legacy_pk,
        high_risk_assets=high_risk,
        critical_risk_assets=critical_risk,
        pqc_migrated_assets=status_dist.get("pqc_migrated", 0),
        hybrid_assets=status_dist.get("hybrid", 0),
        algorithm_distribution=algo_dist,
        priority_distribution=priority_dist,
        migration_status_distribution=status_dist,
    )


@router.get("/{asset_id}", response_model=AssetDetailOut)
def get_asset(asset_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/scan", response_model=ScanResultOut)
def trigger_scan(db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    before_count = db.query(Asset).count()
    result = scan_directory(db)
    record_audit(
        db, actor=user.username, action="discovery_scan", target_type="asset", target_id="*",
        before={"asset_count": before_count},
        after={"created": result.assets_created, "updated": result.assets_updated, "errors": result.errors},
    )
    return ScanResultOut(
        source_dir=result.source_dir, files_scanned=result.files_scanned,
        applications_seen=result.applications_seen, assets_created=result.assets_created,
        assets_updated=result.assets_updated, errors=result.errors,
    )

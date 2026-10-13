from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import MigrationPlanOut
from app.core.security import CurrentUser
from app.db.models import MigrationPlan, PQCRecommendation
from app.migration.planner import plan_for_all_recommendations, plan_for_recommendation
from app.migration.simulator import simulate_all_plans, simulate_plan

router = APIRouter(prefix="/api/v1/migrations", tags=["migrations"])


@router.get("", response_model=list[MigrationPlanOut])
def list_plans(asset_id: str | None = None, status: str | None = None,
                db: Session = Depends(get_db), _=Depends(require_viewer)):
    q = db.query(MigrationPlan)
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    if status:
        q = q.filter_by(status=status)
    return q.order_by(MigrationPlan.created_at.desc()).all()


@router.get("/{plan_id}", response_model=MigrationPlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    plan = db.get(MigrationPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Migration plan not found")
    return plan


@router.post("/recommendation/{recommendation_id}/plan", response_model=MigrationPlanOut)
def create_plan(recommendation_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    rec = db.get(PQCRecommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    plan = plan_for_recommendation(db, rec)
    if plan is None:
        raise HTTPException(status_code=409, detail="Recommendation strategy has no concrete migration target (deferred/agility_prep/manual_review)")
    db.commit()
    record_audit(db, actor=user.username, action="create_migration_plan", target_type="asset", target_id=rec.asset_id,
                 after={"plan_id": plan.id, "target_algorithm_id": plan.target_algorithm_id})
    return plan


@router.post("/plan-all", response_model=list[MigrationPlanOut])
def create_all_plans(db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    plans = plan_for_all_recommendations(db)
    record_audit(db, actor=user.username, action="create_all_migration_plans", target_type="asset", target_id="*",
                 after={"count": len(plans)})
    return plans


@router.post("/{plan_id}/simulate", response_model=MigrationPlanOut)
def simulate_single_plan(plan_id: str, iterations: int = 15, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    plan = db.get(MigrationPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Migration plan not found")
    simulate_plan(db, plan, iterations=iterations)
    record_audit(db, actor=user.username, action="simulate_migration", target_type="migration_plan", target_id=plan_id,
                 after={"performance_impact": plan.performance_impact_json})
    db.refresh(plan)
    return plan


@router.post("/simulate-all")
def simulate_all(iterations: int = 15, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    outcomes = simulate_all_plans(db, iterations=iterations)
    record_audit(db, actor=user.username, action="simulate_all_migrations", target_type="migration_plan", target_id="*",
                 after={"count": len(outcomes)})
    return {"simulated": len(outcomes)}

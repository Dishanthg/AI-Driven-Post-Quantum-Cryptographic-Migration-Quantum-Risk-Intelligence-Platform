"""Migration Planner (design doc Section 26).

Builds a MigrationPlan (+ ordered MigrationStep rows) from a PQCRecommendation
that has a concrete target algorithm - i.e. `pqc_migration` or
`hybrid_migration` strategies only. `deferred`/`manual_review` have no target
to plan against, and `agility_prep` is a precursor to a future plan, not a
migration itself, so none of those three produce a MigrationPlan.

Effort estimation is a documented, deterministic formula over the asset's own
attributes (migration_complexity, asset_criticality, internet_exposure,
strategy) - NOT a hard-coded per-asset constant (Rule 8) and NOT an ML
prediction (there is no ground-truth "actual migration hours" data to train
against; Section 60 lists "absence of real enterprise migration data" as an
explicit, acknowledged limitation). This is an engineering estimate, labeled
as such wherever it is surfaced.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Algorithm, Asset, MigrationPlan, MigrationStep, PQCRecommendation
from app.recommendations.engine import STRATEGY_HYBRID, STRATEGY_PQC

BASE_HOURS = {"low": 4.0, "medium": 12.0, "high": 30.0}
CRITICALITY_MULTIPLIER = {"low": 1.0, "medium": 1.1, "high": 1.25, "critical": 1.5}
INTERNET_EXPOSURE_EXTRA_HOURS = 6.0  # external client/coordination + phased rollout window
HYBRID_EXTRA_HOURS = 8.0  # building and testing two parallel key-establishment code paths

_COMPAT_ESCALATION = {"low": "medium", "medium": "high", "high": "high"}


@dataclass
class EffortEstimate:
    hours: float
    formula: str


def estimate_effort(asset: Asset, strategy: str) -> EffortEstimate:
    base = BASE_HOURS[asset.migration_complexity]
    mult = CRITICALITY_MULTIPLIER[asset.asset_criticality]
    exposure_extra = INTERNET_EXPOSURE_EXTRA_HOURS if asset.internet_exposure else 0.0
    strategy_extra = HYBRID_EXTRA_HOURS if strategy == STRATEGY_HYBRID else 0.0
    hours = base * mult + exposure_extra + strategy_extra
    formula = (
        f"{base:.1f}h[complexity={asset.migration_complexity}] * {mult:.2f}[criticality={asset.asset_criticality}] "
        f"+ {exposure_extra:.1f}h[internet_exposure={asset.internet_exposure}] "
        f"+ {strategy_extra:.1f}h[strategy={strategy}] = {hours:.1f}h"
    )
    return EffortEstimate(hours=round(hours, 1), formula=formula)


def compatibility_risk(asset: Asset) -> str:
    base = asset.migration_complexity
    return _COMPAT_ESCALATION[base] if asset.internet_exposure else base


def _build_steps(plan: MigrationPlan, asset: Asset, current: Algorithm, target: Algorithm, strategy: str) -> list[MigrationStep]:
    steps = [
        MigrationStep(
            plan_id=plan.id, sequence=1, stage="legacy",
            description=f"Baseline: {asset.hostname} currently uses {current.name} for {asset.usage_type}.",
            status="completed",
        )
    ]
    if strategy == STRATEGY_HYBRID:
        steps.append(MigrationStep(
            plan_id=plan.id, sequence=2, stage="hybrid",
            description=f"Deploy hybrid classical+PQC configuration ({target.name}) alongside the existing {current.name} path.",
            status="pending",
        ))
        steps.append(MigrationStep(
            plan_id=plan.id, sequence=3, stage="pqc_enabled",
            description="Full cutover to PQC-only once peer/client ecosystem support is confirmed (future step, not scheduled by this plan).",
            status="pending",
        ))
    else:
        steps.append(MigrationStep(
            plan_id=plan.id, sequence=2, stage="pqc_enabled",
            description=f"Cut over {asset.hostname} from {current.name} to {target.name}.",
            status="pending",
        ))
    return steps


def plan_for_recommendation(db: Session, recommendation: PQCRecommendation) -> MigrationPlan | None:
    if recommendation.strategy not in (STRATEGY_PQC, STRATEGY_HYBRID) or not recommendation.target_algorithm_id:
        return None

    asset = db.get(Asset, recommendation.asset_id)
    current = db.get(Algorithm, asset.algorithm_id)
    target = db.get(Algorithm, recommendation.target_algorithm_id)

    effort = estimate_effort(asset, recommendation.strategy)

    plan = MigrationPlan(
        asset_id=asset.id,
        recommendation_id=recommendation.id,
        current_algorithm_id=current.id,
        target_algorithm_id=target.id,
        priority=_priority_from_recommendation(db, recommendation),
        estimated_effort_hours=effort.hours,
        performance_impact_json={"effort_formula": effort.formula, "note": "Populated with measured benchmark deltas by app.migration.simulator"},
        compatibility_risk=compatibility_risk(asset),
        rollback_strategy=(
            f"Revert {asset.hostname}'s CryptoProvider configuration to {current.name} "
            f"(config-only change under the CryptoProvider abstraction, Section 28); "
            f"{'reissue the TLS certificate against the prior algorithm' if asset.usage_type == 'tls_certificate' else 'no certificate reissuance required'}."
        ),
        verification_criteria=(
            f"1) Roundtrip correctness: generate a fresh {target.name} keypair and confirm "
            f"encapsulate/decapsulate (or sign/verify) succeeds via CryptoProvider. "
            "2) Interoperability: confirm peer/client can complete the handshake against the new configuration in a lab environment. "
            "3) Benchmark regression: confirm latency/size deltas measured by app.migration.simulator are within the documented performance-impact figures shown to stakeholders before rollout."
        ),
        owner="unassigned",
        status="proposed",
    )
    db.add(plan)
    db.flush()

    steps = _build_steps(plan, asset, current, target, recommendation.strategy)
    db.add_all(steps)
    return plan


def _priority_from_recommendation(db: Session, recommendation: PQCRecommendation) -> str:
    from app.db.models import RiskAssessment
    risk = db.get(RiskAssessment, recommendation.risk_assessment_id)
    return risk.priority if risk else "medium"


def plan_for_all_recommendations(db: Session) -> list[MigrationPlan]:
    plans = []
    for rec in db.query(PQCRecommendation).all():
        plan = plan_for_recommendation(db, rec)
        if plan is not None:
            plans.append(plan)
    db.commit()
    return plans


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        plans = plan_for_all_recommendations(session)
        total_hours = sum(p.estimated_effort_hours for p in plans)
        print(f"Generated {len(plans)} migration plans, {total_hours:.1f} estimated hours total.")
    finally:
        session.close()

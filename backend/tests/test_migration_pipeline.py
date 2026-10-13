"""End-to-end domain-layer test: discover -> assess (rule baseline, so no
trained-model dependency) -> recommend -> plan -> simulate, all against an
isolated test database. Uses the rule baseline rather than the ML model so
this test doesn't need a trained artifact; test_ai_risk_engine.py covers the
ML path separately."""
from __future__ import annotations

import datetime as dt

from app.db.models import Algorithm, Asset, Benchmark, BenchmarkRun, MigrationPlan, PQCRecommendation, RiskAssessment
from app.discovery.scanner import scan_directory
from app.migration.planner import plan_for_all_recommendations
from app.migration.simulator import simulate_all_plans
from app.recommendations.engine import STRATEGY_HYBRID, STRATEGY_PQC, decide, recommend_for_all_assets
from app.risk.service import METHOD_RULE, assess_all_assets


def test_full_pipeline_rule_based(db_session):
    scan_directory(db_session)
    assets = db_session.query(Asset).all()
    assert len(assets) == 42

    assessments = assess_all_assets(db_session, method=METHOD_RULE)
    assert len(assessments) == 42
    assert all(a.priority in ("low", "medium", "high", "critical") for a in assessments)
    assert db_session.query(RiskAssessment).count() == 42

    recs = recommend_for_all_assets(db_session)
    assert len(recs) == 42
    assert db_session.query(PQCRecommendation).count() == 42
    # already-PQC/hybrid pilot assets should be flagged manual_review, not re-recommended for migration
    strategies = {r.strategy for r in recs}
    assert strategies <= {"pqc_migration", "hybrid_migration", "deferred", "agility_prep", "manual_review"}

    plans = plan_for_all_recommendations(db_session)
    assert len(plans) > 0
    for plan in plans:
        assert plan.estimated_effort_hours > 0
        assert plan.status == "proposed"
    assert db_session.query(MigrationPlan).count() == len(plans)

    outcomes = simulate_all_plans(db_session, iterations=5)
    assert len(outcomes) == len(plans)
    for plan in db_session.query(MigrationPlan).all():
        assert plan.status == "in_progress"
        assert plan.performance_impact_json.get("simulated") is True
        for step in plan.steps:
            if step.status in ("completed", "failed"):
                assert step.simulated_result_json.get("roundtrip_verified") in (True, False)
                if step.status == "completed":
                    assert step.simulated_result_json["roundtrip_verified"] is True


def test_migration_plans_only_created_for_pqc_or_hybrid_strategy(db_session):
    scan_directory(db_session)
    assess_all_assets(db_session, method=METHOD_RULE)
    recs = recommend_for_all_assets(db_session)
    plans = plan_for_all_recommendations(db_session)

    actionable_rec_ids = {r.id for r in recs if r.strategy in (STRATEGY_PQC, STRATEGY_HYBRID)}
    planned_rec_ids = {p.recommendation_id for p in plans}
    assert planned_rec_ids == actionable_rec_ids


def _long_lived_tls_cert_asset() -> Asset:
    return Asset(
        id="test-asset-tls-cert", application_id="test-app", hostname="edge.example.lab",
        usage_type="tls_certificate", algorithm_id="ECDSA-P256", key_size_bits=256,
        data_sensitivity="high", data_lifetime_years=15, asset_criticality="critical",
        internet_exposure=True, migration_complexity="low", current_status="legacy",
    )


def _critical_risk_assessment() -> RiskAssessment:
    return RiskAssessment(id="test-risk-1", asset_id="test-asset-tls-cert", method="rule_baseline",
                           risk_score=0.9, priority="critical", confidence=1.0)


def test_recommendation_falls_back_to_hash_based_signature_without_benchmark_data(db_session):
    """Without any real benchmark data present (db=None), the recommender
    keeps its original conservative lifetime-only behavior: a long-lived,
    internet-facing TLS certificate still gets the hash-based SLH-DSA choice."""
    algorithm = db_session.get(Algorithm, "ECDSA-P256")
    decision = decide(_long_lived_tls_cert_asset(), algorithm, _critical_risk_assessment(), db=None)
    assert decision.target_algorithm_id == "SLH-DSA-SHA2-128F"


def test_recommendation_uses_real_benchmark_data_to_avoid_tls_handshake_bloat(db_session):
    """With a REAL (not fabricated) benchmark run on record showing
    SLH-DSA-SHA2-128F's actual signature size (17088 bytes, matching this
    platform's own measured research/tables/benchmark_sweep.csv value)
    exceeds the TLS handshake budget, the recommender should switch a
    long-lived, internet-facing TLS-certificate asset to ML-DSA-65 instead -
    a genuine performance-requirement input (design doc Section 24), not
    merely a lifetime heuristic."""
    benchmark = Benchmark(id="bench-1", name="pqclean_sign", operation="sign", algorithm_id="SLH-DSA-SHA2-128F")
    db_session.add(benchmark)
    db_session.flush()
    db_session.add(BenchmarkRun(
        id="bench-run-1", benchmark_id=benchmark.id, iterations=30,
        completed_at=dt.datetime.now(dt.UTC), status="completed",
        summary_stats_json={"ciphertext_or_signature_bytes": 17088},
    ))
    db_session.commit()

    algorithm = db_session.get(Algorithm, "ECDSA-P256")
    decision = decide(_long_lived_tls_cert_asset(), algorithm, _critical_risk_assessment(), db=db_session)
    assert decision.target_algorithm_id == "ML-DSA-65"
    assert "17088 bytes" in decision.rationale
    assert "handshake" in decision.rationale.lower()


def test_dh_asset_is_simulatable(db_session):
    """Regression guard: DH-2048 (api-gateway's legacy mTLS asset) must be
    operable end-to-end, not just classified - this caught a missing
    DHProvider during development."""
    scan_directory(db_session)
    assess_all_assets(db_session, method=METHOD_RULE)
    recommend_for_all_assets(db_session)
    plans = plan_for_all_recommendations(db_session)
    dh_plans = [p for p in plans if p.current_algorithm_id == "DH-2048"]
    assert len(dh_plans) >= 1
    simulate_all_plans(db_session, iterations=3)
    for plan in dh_plans:
        db_session.refresh(plan)
        assert plan.status == "in_progress"

"""Bridges the relational asset inventory to the AI risk engine (design doc
Section 19/20/22). Builds a RiskAssessment (+ RiskFactor rows) for a real
Asset, using either the rule baseline or the trained ML model + SHAP
explainer - the same feature schema (app.ai.features) both paths were
evaluated on in Experiment 3, so results are directly comparable per-asset.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.ai.explain import load_active_explainer
from app.ai.features import AssetFeatures
from app.ai.model_registry import get_active_model_version
from app.ai.rule_baseline import assess as rule_assess
from app.core.metrics import MODEL_INFERENCE_LATENCY
from app.crypto import registry as algo_registry
from app.db.models import Algorithm, Asset, RiskAssessment, RiskFactor

METHOD_RULE = "rule_baseline"
METHOD_ML = "ml_model"


def _features_for_asset(db: Session, asset: Asset) -> AssetFeatures:
    algorithm = db.get(Algorithm, asset.algorithm_id)
    if algorithm is None:
        # fall back to the in-code registry if the DB row hasn't been seeded yet
        spec = algo_registry.get(asset.algorithm_id)
        quantum_vulnerability = spec.quantum_vulnerability
    else:
        quantum_vulnerability = algorithm.quantum_vulnerability

    return AssetFeatures.from_raw(
        quantum_vulnerability=quantum_vulnerability,
        key_size_bits=asset.key_size_bits,
        asset_criticality=asset.asset_criticality,
        data_sensitivity=asset.data_sensitivity,
        data_lifetime_years=asset.data_lifetime_years,
        internet_exposure=asset.internet_exposure,
        migration_complexity=asset.migration_complexity,
        business_importance=asset.asset_criticality,  # no separate business_importance on Asset; criticality doubles
        # as the business-importance signal at asset granularity (Application.business_importance is
        # the application-level counterpart, folded in below).
    )


def assess_asset(db: Session, asset: Asset, method: str = METHOD_ML) -> RiskAssessment:
    features = _features_for_asset(db, asset)
    # blend in application-level business_importance if it differs from asset criticality
    if asset.application and asset.application.business_importance:
        from app.ai.features import ORDINAL_MAP
        app_importance = ORDINAL_MAP.get(asset.application.business_importance, features.business_importance)
        features.business_importance = max(features.business_importance, app_importance)

    if method == METHOD_RULE:
        result = rule_assess(features)
        model_version_id = None
        factor_pairs = result["top_factors"]
    elif method == METHOD_ML:
        explainer = load_active_explainer()
        t0 = time.perf_counter()
        result = explainer.predict_and_explain(features.to_vector())
        MODEL_INFERENCE_LATENCY.labels(explainer.algorithm).observe(time.perf_counter() - t0)
        active_version = get_active_model_version(db)
        model_version_id = active_version.id if active_version else None
        factor_pairs = result["top_factors"]
    else:
        raise ValueError(f"Unknown risk assessment method: {method!r}")

    assessment = RiskAssessment(
        asset_id=asset.id,
        method=method,
        model_version_id=model_version_id,
        risk_score=result["risk_score"],
        priority=result["priority"],
        confidence=result["confidence"],
        features_json={
            "quantum_vulnerability": features.quantum_vulnerability,
            "key_size_norm": features.key_size_norm,
            "asset_criticality": features.asset_criticality,
            "data_sensitivity": features.data_sensitivity,
            "data_lifetime_years_norm": features.data_lifetime_years_norm,
            "internet_exposure": features.internet_exposure,
            "migration_complexity": features.migration_complexity,
            "business_importance": features.business_importance,
        },
    )
    db.add(assessment)
    db.flush()

    for name, contribution in factor_pairs:
        db.add(RiskFactor(assessment_id=assessment.id, feature_name=name, contribution=float(contribution)))

    return assessment


def assess_all_assets(db: Session, method: str = METHOD_ML) -> list[RiskAssessment]:
    assessments = []
    for asset in db.query(Asset).all():
        assessments.append(assess_asset(db, asset, method=method))
    db.commit()
    return assessments


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        results = assess_all_assets(session, method=METHOD_ML)
        by_priority: dict[str, int] = {}
        for r in results:
            by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
        print(f"Assessed {len(results)} assets. Priority distribution: {by_priority}")
    finally:
        session.close()

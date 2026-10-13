"""Static rule-based risk scorer - the BASELINE for Experiments 3/4 (design doc
Section 20). This is what an organization could hand-write without any ML: a
transparent, auditable weighted sum over the same feature schema used by the
ML models (app/ai/features.py), with fixed, documented weights and NO access
to the nonlinear interaction term used to construct the synthetic ground-truth
label (app/ai/dataset.py) - it must earn any predictive advantage on its own.
"""
from __future__ import annotations

from app.ai.features import AssetFeatures

RULE_WEIGHTS = {
    "quantum_vulnerability": 0.30,   # /2
    "asset_criticality": 0.22,       # /3
    "data_sensitivity": 0.16,        # /3
    "data_lifetime_years_norm": 0.11,
    "internet_exposure": 0.14,
    "business_importance": 0.07,     # /3
}
PRIORITY_THRESHOLDS = {"critical": 0.72, "high": 0.55, "medium": 0.35}


def score(features: AssetFeatures) -> float:
    s = (
        RULE_WEIGHTS["quantum_vulnerability"] * (features.quantum_vulnerability / 2.0)
        + RULE_WEIGHTS["asset_criticality"] * (features.asset_criticality / 3.0)
        + RULE_WEIGHTS["data_sensitivity"] * (features.data_sensitivity / 3.0)
        + RULE_WEIGHTS["data_lifetime_years_norm"] * features.data_lifetime_years_norm
        + RULE_WEIGHTS["internet_exposure"] * features.internet_exposure
        + RULE_WEIGHTS["business_importance"] * (features.business_importance / 3.0)
    )
    return max(0.0, min(1.0, s))


def priority(risk_score: float) -> str:
    if risk_score >= PRIORITY_THRESHOLDS["critical"]:
        return "critical"
    if risk_score >= PRIORITY_THRESHOLDS["high"]:
        return "high"
    if risk_score >= PRIORITY_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def assess(features: AssetFeatures) -> dict:
    s = score(features)
    top_factors = sorted(
        (
            ("quantum_vulnerability", RULE_WEIGHTS["quantum_vulnerability"] * features.quantum_vulnerability / 2.0),
            ("asset_criticality", RULE_WEIGHTS["asset_criticality"] * features.asset_criticality / 3.0),
            ("data_sensitivity", RULE_WEIGHTS["data_sensitivity"] * features.data_sensitivity / 3.0),
            ("data_lifetime", RULE_WEIGHTS["data_lifetime_years_norm"] * features.data_lifetime_years_norm),
            ("internet_exposure", RULE_WEIGHTS["internet_exposure"] * features.internet_exposure),
            ("business_importance", RULE_WEIGHTS["business_importance"] * features.business_importance / 3.0),
        ),
        key=lambda kv: -kv[1],
    )
    return {
        "method": "rule_baseline",
        "risk_score": s,
        "priority": priority(s),
        "confidence": 1.0,  # deterministic function, always "fully confident" in its own (simple) logic
        "top_factors": top_factors[:3],
    }

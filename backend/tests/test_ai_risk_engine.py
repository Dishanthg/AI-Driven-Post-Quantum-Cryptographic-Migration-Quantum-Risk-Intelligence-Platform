from __future__ import annotations

from app.ai.features import AssetFeatures
from app.ai.rule_baseline import assess as rule_assess


def test_rule_baseline_is_deterministic():
    feats = AssetFeatures.from_raw(
        quantum_vulnerability="quantum_vulnerable", key_size_bits=2048, asset_criticality="high",
        data_sensitivity="high", data_lifetime_years=5, internet_exposure=True,
        migration_complexity="medium", business_importance="high",
    )
    r1 = rule_assess(feats)
    r2 = rule_assess(feats)
    assert r1["risk_score"] == r2["risk_score"]
    assert r1["priority"] == r2["priority"]


def test_rule_baseline_monotonic_in_criticality():
    low = AssetFeatures.from_raw("quantum_vulnerable", 2048, "low", "low", 1, False, "low", "low")
    high = AssetFeatures.from_raw("quantum_vulnerable", 2048, "critical", "critical", 1, False, "low", "critical")
    assert rule_assess(low)["risk_score"] < rule_assess(high)["risk_score"]


def test_rule_baseline_pqc_asset_scores_lower_than_vulnerable_asset():
    vulnerable = AssetFeatures.from_raw("quantum_vulnerable", 2048, "high", "high", 5, True, "medium", "high")
    safe = AssetFeatures.from_raw("not_significantly_affected", 2048, "high", "high", 5, True, "medium", "high")
    assert rule_assess(safe)["risk_score"] < rule_assess(vulnerable)["risk_score"]


def test_rule_baseline_score_bounded():
    for qv in ("quantum_vulnerable", "quantum_weakened", "not_significantly_affected"):
        feats = AssetFeatures.from_raw(qv, 4096, "critical", "critical", 20, True, "high", "critical")
        r = rule_assess(feats)
        assert 0.0 <= r["risk_score"] <= 1.0
        assert r["priority"] in ("low", "medium", "high", "critical")


def test_train_and_explain_end_to_end(small_trained_model):
    """Real training run (see conftest.small_trained_model) + real SHAP explanation
    against the freshly trained artifact - not a mocked model."""
    from app.ai.explain import load_active_explainer

    out = small_trained_model
    assert out["best_model"] in ("logistic_regression", "random_forest", "xgboost")
    assert 0.0 <= out["results"][out["best_model"]]["macro_f1"] <= 1.0
    # rule baseline must have been evaluated on the exact same held-out split for a fair comparison
    assert "rule_baseline" in out["results"]

    explainer = load_active_explainer()
    feats = AssetFeatures.from_raw("quantum_vulnerable", 256, "critical", "critical", 15, True, "high", "critical")
    result = explainer.predict_and_explain(feats.to_vector())
    assert result["priority"] in ("low", "medium", "high", "critical")
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["top_factors"]) == 3
    assert len(result["all_factors"]) == len(feats.to_vector())

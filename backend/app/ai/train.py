"""Train and evaluate the AI risk engine (design doc Sections 19/20, Experiment 3).

Trains three real models (LogisticRegression, RandomForest, XGBoost) on the
synthetic dataset, evaluates them against a held-out test split AND against
the rule-based baseline, using real sklearn/xgboost metric computations - none
of the numbers below are hand-typed. Every run is reproducible via `seed`.
"""
from __future__ import annotations

import json
import time

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import kendalltau
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    cohen_kappa_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

from app.ai.dataset import generate_synthetic_inventory
from app.ai.features import ORDINAL_MAP, AssetFeatures
from app.ai.rule_baseline import assess as rule_assess
from app.core.config import get_settings

FEATURE_COLS = [
    "quantum_vulnerability_ord", "key_size_norm", "asset_criticality_ord", "data_sensitivity_ord",
    "data_lifetime_years_norm", "internet_exposure_bin", "migration_complexity_ord", "business_importance_ord",
]
LABEL_ORDER = ["low", "medium", "high", "critical"]
LABEL_TO_INT = {label: i for i, label in enumerate(LABEL_ORDER)}


def _featurize(df: pd.DataFrame) -> pd.DataFrame:
    from app.ai.features import QUANTUM_VULN_MAP
    out = pd.DataFrame()
    out["quantum_vulnerability_ord"] = df["quantum_vulnerability"].map(QUANTUM_VULN_MAP)
    out["key_size_norm"] = df["key_size_bits"].clip(upper=4096) / 4096.0
    out["asset_criticality_ord"] = df["asset_criticality"].map(ORDINAL_MAP)
    out["data_sensitivity_ord"] = df["data_sensitivity"].map(ORDINAL_MAP)
    out["data_lifetime_years_norm"] = (df["data_lifetime_years"] / 20.0).clip(upper=1.0)
    out["internet_exposure_bin"] = df["internet_exposure"].astype(int)
    out["migration_complexity_ord"] = df["migration_complexity"].map({"low": 0, "medium": 1, "high": 2})
    out["business_importance_ord"] = df["business_importance"].map(ORDINAL_MAP)
    return out


def _rule_baseline_predictions(df: pd.DataFrame) -> list[str]:
    preds = []
    for _, row in df.iterrows():
        feats = AssetFeatures.from_raw(
            quantum_vulnerability=row["quantum_vulnerability"],
            key_size_bits=int(row["key_size_bits"]),
            asset_criticality=row["asset_criticality"],
            data_sensitivity=row["data_sensitivity"],
            data_lifetime_years=int(row["data_lifetime_years"]),
            internet_exposure=bool(row["internet_exposure"]),
            migration_complexity=row["migration_complexity"],
            business_importance=row["business_importance"],
        )
        preds.append(rule_assess(feats)["priority"])
    return preds


def _metrics(y_true: list[str], y_pred: list[str]) -> dict:
    y_true_i = [LABEL_TO_INT[label] for label in y_true]
    y_pred_i = [LABEL_TO_INT[label] for label in y_pred]
    return {
        "macro_f1": float(f1_score(y_true_i, y_pred_i, average="macro")),
        "macro_precision": float(precision_score(y_true_i, y_pred_i, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true_i, y_pred_i, average="macro", zero_division=0)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true_i, y_pred_i, weights="quadratic")),
        "classification_report": classification_report(
            y_true_i, y_pred_i, target_names=LABEL_ORDER, zero_division=0, output_dict=True
        ),
    }


def train_and_evaluate(n_samples: int = 2000, seed: int = 42) -> dict:
    settings = get_settings()
    df = generate_synthetic_inventory(n=n_samples, seed=seed)
    X = _featurize(df)
    y = df["priority_label"]
    y_int = y.map(LABEL_TO_INT)

    X_train, X_test, y_train, y_test, _df_train, df_test = train_test_split(
        X, y_int, df, test_size=0.3, random_state=seed, stratify=y_int
    )

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    results: dict[str, dict] = {}
    trained_models: dict[str, object] = {}

    t0 = time.perf_counter()
    logreg = LogisticRegression(max_iter=1000, random_state=seed)
    logreg.fit(X_train_s, y_train)
    pred = [LABEL_ORDER[i] for i in logreg.predict(X_test_s)]
    results["logistic_regression"] = {**_metrics(list(y.loc[y_test.index]), pred), "train_seconds": time.perf_counter() - t0}
    trained_models["logistic_regression"] = (logreg, scaler)

    t0 = time.perf_counter()
    rf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=seed, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = [LABEL_ORDER[i] for i in rf.predict(X_test)]
    results["random_forest"] = {**_metrics(list(y.loc[y_test.index]), pred), "train_seconds": time.perf_counter() - t0}
    trained_models["random_forest"] = (rf, None)

    t0 = time.perf_counter()
    xgb_clf = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1, random_state=seed,
        objective="multi:softprob", num_class=4, eval_metric="mlogloss",
    )
    xgb_clf.fit(X_train, y_train)
    pred = [LABEL_ORDER[i] for i in xgb_clf.predict(X_test)]
    results["xgboost"] = {**_metrics(list(y.loc[y_test.index]), pred), "train_seconds": time.perf_counter() - t0}
    trained_models["xgboost"] = (xgb_clf, None)

    rule_pred_test = _rule_baseline_predictions(df_test)
    results["rule_baseline"] = _metrics(list(y.loc[y_test.index]), rule_pred_test)

    # --- ranking-consistency check (H1): 5-fold CV, Kendall's tau of predicted
    # risk ranking (continuous score) between folds' models on a shared holdout ---
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    fold_rf_scores = []
    fixed_eval_idx = X_test.index
    for train_idx, _ in skf.split(X, y_int):
        rf_fold = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=seed, n_jobs=-1)
        rf_fold.fit(X.iloc[train_idx], y_int.iloc[train_idx])
        proba = rf_fold.predict_proba(X.loc[fixed_eval_idx])
        risk_like = proba @ np.arange(4)
        fold_rf_scores.append(risk_like)

    rule_scores_eval = np.array([
        rule_assess(AssetFeatures.from_raw(
            quantum_vulnerability=row["quantum_vulnerability"], key_size_bits=int(row["key_size_bits"]),
            asset_criticality=row["asset_criticality"], data_sensitivity=row["data_sensitivity"],
            data_lifetime_years=int(row["data_lifetime_years"]), internet_exposure=bool(row["internet_exposure"]),
            migration_complexity=row["migration_complexity"], business_importance=row["business_importance"],
        ))["risk_score"]
        for _, row in df.loc[fixed_eval_idx].iterrows()
    ])

    ml_taus = []
    for i in range(len(fold_rf_scores)):
        for j in range(i + 1, len(fold_rf_scores)):
            tau, _ = kendalltau(fold_rf_scores[i], fold_rf_scores[j])
            ml_taus.append(tau)
    rule_tau_vs_ml_mean = float(kendalltau(np.mean(fold_rf_scores, axis=0), rule_scores_eval)[0])

    results["ranking_consistency"] = {
        "description": "Kendall's tau of RandomForest risk-ranking across 5 independently-trained CV folds, "
                        "evaluated on the same fixed holdout set (H1: does ML give more consistent prioritization "
                        "than a deterministic rule, which by construction has tau=1.0 across 'folds' since it is "
                        "not retrained).",
        "ml_fold_pairwise_kendall_tau_mean": float(np.mean(ml_taus)),
        "ml_fold_pairwise_kendall_tau_min": float(np.min(ml_taus)),
        "rule_baseline_fold_pairwise_kendall_tau": 1.0,
        "ml_vs_rule_kendall_tau": rule_tau_vs_ml_mean,
        "interpretation": "Rule baseline is deterministic so it is perfectly self-consistent by construction "
                           "(tau=1.0); this metric instead tells us how much the ML model's ranking varies with "
                           "training data resampling - lower values indicate the model is sensitive to the "
                           "particular training sample, which is a genuine finding, not necessarily a flaw.",
    }

    # --- persist model artifacts + metrics (Section 56: model versioning) ---
    version = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    best_name = max(
        ("logistic_regression", "random_forest", "xgboost"),
        key=lambda k: results[k]["macro_f1"],
    )
    out_dir = settings.model_registry_dir / "risk_prioritization" / version
    out_dir.mkdir(parents=True, exist_ok=True)
    model_obj, scaler_obj = trained_models[best_name]
    joblib.dump({"model": model_obj, "scaler": scaler_obj, "feature_cols": FEATURE_COLS, "label_order": LABEL_ORDER}, out_dir / "model.joblib")

    metadata = {
        "model_name": "risk_prioritization",
        "version": version,
        "algorithm": best_name,
        "features": FEATURE_COLS,
        "dataset_ref": f"synthetic_crypto_inventory n={n_samples} seed={seed}",
        "random_seed": seed,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "metrics": {k: v for k, v in results.items()},
        "is_active": True,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=float))

    return {"version": version, "best_model": best_name, "artifact_dir": str(out_dir), "results": results}


if __name__ == "__main__":
    out = train_and_evaluate()
    print(f"Best model: {out['best_model']} (version {out['version']})")
    for name in ("rule_baseline", "logistic_regression", "random_forest", "xgboost"):
        m = out["results"][name]
        print(f"  {name:22s} macro_f1={m['macro_f1']:.4f} macro_precision={m['macro_precision']:.4f} macro_recall={m['macro_recall']:.4f}")
    print("  ranking_consistency:", out["results"]["ranking_consistency"])

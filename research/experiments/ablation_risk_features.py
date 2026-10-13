"""Ablation study for the AI risk engine (design doc Section 40).

Removes one feature at a time from the risk-prioritization feature set and
re-trains, measuring the change in macro-F1/kappa on the same held-out split
used by app.ai.train. Uses LogisticRegression only (the best-performing model
in the full-feature run recorded in research/tables/risk_model_comparison.md)
so the ablation isolates the effect of feature removal rather than mixing it
with model-choice variance.

This does NOT write to backend/artifacts/models/ (the production model
registry) - it is a separate, standalone measurement, never marked "active".

Run: python -m research.experiments.ablation_risk_features   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ai.dataset import generate_synthetic_inventory  # noqa: E402
from app.ai.train import FEATURE_COLS, LABEL_ORDER, LABEL_TO_INT, _featurize, _metrics  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

SEED = 42
N_SAMPLES = 2000


def _train_eval(X_cols: list[str], X_full, y, y_int, seed: int = SEED) -> dict:
    X = X_full[X_cols]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_int, test_size=0.3, random_state=seed, stratify=y_int
    )
    scaler = StandardScaler().fit(X_train)
    model = LogisticRegression(max_iter=1000, random_state=seed)
    model.fit(scaler.transform(X_train), y_train)
    pred = [LABEL_ORDER[i] for i in model.predict(scaler.transform(X_test))]
    y_true = [LABEL_ORDER[i] for i in y_test]
    return _metrics(y_true, pred)


def run_ablation(n_samples: int = N_SAMPLES, seed: int = SEED) -> dict:
    df = generate_synthetic_inventory(n=n_samples, seed=seed)
    X_full = _featurize(df)
    y = df["priority_label"]
    y_int = y.map(LABEL_TO_INT)

    baseline = _train_eval(FEATURE_COLS, X_full, y, y_int, seed)

    rows = [{
        "removed_feature": "(none - full feature set)",
        "macro_f1": baseline["macro_f1"],
        "macro_precision": baseline["macro_precision"],
        "macro_recall": baseline["macro_recall"],
        "quadratic_weighted_kappa": baseline["quadratic_weighted_kappa"],
        "delta_macro_f1_vs_full": 0.0,
    }]

    for feature in FEATURE_COLS:
        remaining = [c for c in FEATURE_COLS if c != feature]
        m = _train_eval(remaining, X_full, y, y_int, seed)
        rows.append({
            "removed_feature": feature,
            "macro_f1": m["macro_f1"],
            "macro_precision": m["macro_precision"],
            "macro_recall": m["macro_recall"],
            "quadratic_weighted_kappa": m["quadratic_weighted_kappa"],
            "delta_macro_f1_vs_full": m["macro_f1"] - baseline["macro_f1"],
        })

    rows.sort(key=lambda r: r["delta_macro_f1_vs_full"])
    return {
        "experiment_id": "ablation_risk_features",
        "model": "logistic_regression (best full-feature performer; see research/tables/risk_model_comparison.md)",
        "dataset_ref": f"synthetic_crypto_inventory n={n_samples} seed={seed}",
        "full_feature_set": FEATURE_COLS,
        "rows": rows,
    }


def write_outputs(result: dict) -> None:
    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_risk_features.json").write_text(json.dumps(result, indent=2))

    lines = [
        "# Ablation study: AI risk engine features\n",
        f"Model: {result['model']}\n",
        "One feature removed at a time, re-trained and re-evaluated on the same "
        "70/30 stratified split (seed=42) used elsewhere in this project. "
        "Sorted by impact (most damaging removal first).\n",
        "| removed feature | macro_f1 | Δ macro_f1 vs. full | quadratic_weighted_kappa |",
        "|---|---|---|---|",
    ]
    for r in result["rows"]:
        lines.append(
            f"| {r['removed_feature']} | {r['macro_f1']:.4f} | {r['delta_macro_f1_vs_full']:+.4f} | "
            f"{r['quadratic_weighted_kappa']:.4f} |"
        )
    (out_dir / "ablation_risk_features.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    result = run_ablation()
    write_outputs(result)
    for r in result["rows"]:
        print(f"  removed={r['removed_feature']:35s} macro_f1={r['macro_f1']:.4f}  delta={r['delta_macro_f1_vs_full']:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

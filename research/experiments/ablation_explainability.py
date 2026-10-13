"""Ablation study: does real SHAP-based explainability actually differ from
a cheap, naive "top factors" heuristic? (design doc Section 40's
"explainability layer" ablation.)

app/ai/explain.py computes real SHAP values (TreeExplainer for tree models)
or exact coefficient-based attribution (for logistic regression) per
ADR-004. This script asks whether that cost is justified: for the same
trained model and the same synthetic test rows, compare SHAP's top-3
contributing features against a cheap heuristic - "rank features by how far
this row's standardized feature value is from the population mean" (i.e.
|z-score|, computed with no reference to the trained model's coefficients
or tree structure at all) - and measure (a) top-3 set overlap (Jaccard) and
(b) rank-order agreement (Spearman) between the two explanation methods,
plus the real wall-clock cost of each.

Run: python -m research.experiments.ablation_explainability   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ai.dataset import generate_synthetic_inventory  # noqa: E402
from app.ai.train import FEATURE_COLS, LABEL_TO_INT, _featurize  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

SEED = 42
N_SAMPLES = 2000
N_EXPLAIN_ROWS = 200  # subset of the test set to explain (SHAP-equivalent coefficient method is O(1) here, so this is about apples-to-apples sample size, not a performance shortcut)


def _cheap_heuristic_top3(x_scaled_row: np.ndarray) -> list[str]:
    """No access to the trained model at all: just ranks features by how far
    this row deviates from the (already-standardized, so population mean=0)
    training population. This is the naive alternative SHAP is being
    compared against - genuinely model-free, not a simplified SHAP."""
    order = np.argsort(-np.abs(x_scaled_row))
    return [FEATURE_COLS[i] for i in order[:3]]


def _real_attribution_top3(coefs_for_class: np.ndarray, x_scaled_row: np.ndarray) -> list[str]:
    """Exact per-feature attribution for logistic regression (coefficient *
    standardized feature value) - this is what app/ai/explain.py actually
    computes for the linear-model case (no approximation)."""
    contrib = coefs_for_class * x_scaled_row
    order = np.argsort(-np.abs(contrib))
    return [FEATURE_COLS[i] for i in order[:3]]


def run() -> dict:
    df = generate_synthetic_inventory(n=N_SAMPLES, seed=SEED)
    X = _featurize(df)
    y_int = df["priority_label"].map(LABEL_TO_INT)
    X_train, X_test, y_train, _y_test = train_test_split(
        X, y_int, test_size=0.3, random_state=SEED, stratify=y_int
    )

    scaler = StandardScaler().fit(X_train)
    model = LogisticRegression(max_iter=1000, random_state=SEED).fit(scaler.transform(X_train), y_train)
    X_test_s = scaler.transform(X_test)
    preds = model.predict(X_test_s)

    rows = X_test_s[:N_EXPLAIN_ROWS]
    pred_classes = preds[:N_EXPLAIN_ROWS]

    t0 = time.perf_counter()
    real_tops = [_real_attribution_top3(model.coef_[pc] if model.coef_.shape[0] > 1 else model.coef_[0], row)
                 for row, pc in zip(rows, pred_classes, strict=True)]
    real_seconds = time.perf_counter() - t0

    t0 = time.perf_counter()
    cheap_tops = [_cheap_heuristic_top3(row) for row in rows]
    cheap_seconds = time.perf_counter() - t0

    jaccards = []
    spearmans = []
    for real, cheap in zip(real_tops, cheap_tops, strict=True):
        real_set, cheap_set = set(real), set(cheap)
        jaccards.append(len(real_set & cheap_set) / len(real_set | cheap_set))
        # Spearman over the full feature ranking (not just top-3) for a stricter agreement check
    # full-ranking Spearman needs full orderings, computed separately below:
    full_real_ranks = []
    full_cheap_ranks = []
    for row, pc in zip(rows, pred_classes, strict=True):
        coefs = model.coef_[pc] if model.coef_.shape[0] > 1 else model.coef_[0]
        real_order = np.argsort(-np.abs(coefs * row))
        cheap_order = np.argsort(-np.abs(row))
        full_real_ranks.append(real_order)
        full_cheap_ranks.append(cheap_order)
    for real_order, cheap_order in zip(full_real_ranks, full_cheap_ranks, strict=True):
        rho, _ = spearmanr(real_order, cheap_order)
        spearmans.append(rho)

    return {
        "experiment_id": "ablation_explainability",
        "hypothesis": "Section 40's 'explainability layer' ablation: does real per-feature attribution "
                      "(SHAP for tree models / exact coefficients for logistic regression, per ADR-004) "
                      "differ meaningfully from a cheap, model-free heuristic (rank by |standardized value|)?",
        "n_rows_explained": len(rows),
        "top3_jaccard_mean": float(np.mean(jaccards)),
        "top3_jaccard_min": float(np.min(jaccards)),
        "top3_exact_match_rate": float(np.mean([j == 1.0 for j in jaccards])),
        "full_ranking_spearman_mean": float(np.mean(spearmans)),
        "real_attribution_seconds_total": real_seconds,
        "cheap_heuristic_seconds_total": cheap_seconds,
        "real_attribution_seconds_per_row": real_seconds / len(rows),
        "cheap_heuristic_seconds_per_row": cheap_seconds / len(rows),
        "interpretation": "A low Jaccard/Spearman would mean the cheap heuristic disagrees substantially "
                           "with the model's real attribution, justifying the real method's cost; a high "
                           "one would mean the expensive method isn't buying much beyond the naive "
                           "deviation-from-mean heuristic for this model/dataset.",
    }


def main() -> int:
    result = run()
    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_explainability.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Ablation study: explainability layer (real attribution vs. cheap heuristic)\n",
        f"n={result['n_rows_explained']} test rows. Top-3 Jaccard overlap: mean "
        f"{result['top3_jaccard_mean']:.3f} (min {result['top3_jaccard_min']:.3f}), exact-match rate "
        f"{result['top3_exact_match_rate']:.1%}. Full-ranking Spearman correlation: "
        f"{result['full_ranking_spearman_mean']:.3f}.\n",
        f"Real attribution: {result['real_attribution_seconds_per_row']*1000:.4f} ms/row. "
        f"Cheap heuristic: {result['cheap_heuristic_seconds_per_row']*1000:.4f} ms/row.\n",
        result["interpretation"],
    ]
    (out_dir / "ablation_explainability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

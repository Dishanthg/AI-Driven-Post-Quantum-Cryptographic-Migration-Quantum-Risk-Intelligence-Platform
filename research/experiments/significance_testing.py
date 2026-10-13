"""Statistical significance testing for the AI risk model comparison
(design doc Section 41 / Rule: "do not automatically claim statistical
significance").

Experiment 3 (app/ai/train.py) reports point-estimate macro-F1 for the rule
baseline and three trained models on a single 70/30 split. This script asks
the harder question: are the differences between those point estimates
distinguishable from resampling noise, or could they plausibly be zero?

Method: paired bootstrap over the test-set rows (each resample draws the
same resampled row indices for every model, preserving the pairing) plus a
paired permutation test as a second, non-parametric check. Both are run on
REAL model predictions from a real retraining run (same seed/hyperparameters
as app/ai/train.py) - no simulated or assumed effect sizes.

Run: python -m research.experiments.significance_testing   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import xgboost as xgb  # noqa: E402
from app.ai.dataset import generate_synthetic_inventory  # noqa: E402
from app.ai.features import AssetFeatures  # noqa: E402
from app.ai.rule_baseline import assess as rule_assess  # noqa: E402
from app.ai.train import LABEL_ORDER, LABEL_TO_INT, _featurize  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

SEED = 42
N_SAMPLES = 2000
N_BOOTSTRAP = 2000
N_PERMUTATIONS = 2000


def _rule_predictions(df) -> np.ndarray:
    preds = []
    for _, row in df.iterrows():
        feats = AssetFeatures.from_raw(
            quantum_vulnerability=row["quantum_vulnerability"], key_size_bits=int(row["key_size_bits"]),
            asset_criticality=row["asset_criticality"], data_sensitivity=row["data_sensitivity"],
            data_lifetime_years=int(row["data_lifetime_years"]), internet_exposure=bool(row["internet_exposure"]),
            migration_complexity=row["migration_complexity"], business_importance=row["business_importance"],
        )
        preds.append(LABEL_TO_INT[rule_assess(feats)["priority"]])
    return np.array(preds)


def _train_all(seed: int = SEED, n_samples: int = N_SAMPLES):
    df = generate_synthetic_inventory(n=n_samples, seed=seed)
    X = _featurize(df)
    y_int = df["priority_label"].map(LABEL_TO_INT)

    X_train, X_test, y_train, y_test, _df_train, df_test = train_test_split(
        X, y_int, df, test_size=0.3, random_state=seed, stratify=y_int
    )
    y_test_arr = y_test.to_numpy()

    scaler = StandardScaler().fit(X_train)
    logreg = LogisticRegression(max_iter=1000, random_state=seed).fit(scaler.transform(X_train), y_train)
    rf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=seed, n_jobs=-1).fit(X_train, y_train)
    xgb_clf = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1, random_state=seed,
        objective="multi:softprob", num_class=4, eval_metric="mlogloss",
    ).fit(X_train, y_train)

    preds = {
        "rule_baseline": _rule_predictions(df_test),
        "logistic_regression": logreg.predict(scaler.transform(X_test)),
        "random_forest": rf.predict(X_test),
        "xgboost": xgb_clf.predict(X_test),
    }
    return y_test_arr, preds


def _macro_f1(y_true, y_pred) -> float:
    return f1_score(y_true, y_pred, average="macro", labels=list(range(len(LABEL_ORDER))), zero_division=0)


def paired_bootstrap_ci(y_true, pred_a, pred_b, n_boot: int = N_BOOTSTRAP, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs[i] = _macro_f1(y_true[idx], pred_a[idx]) - _macro_f1(y_true[idx], pred_b[idx])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "observed_diff": float(_macro_f1(y_true, pred_a) - _macro_f1(y_true, pred_b)),
        "bootstrap_mean_diff": float(diffs.mean()),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "ci95_excludes_zero": bool(lo > 0 or hi < 0),
    }


def paired_permutation_test(y_true, pred_a, pred_b, n_perm: int = N_PERMUTATIONS, seed: int = SEED) -> dict:
    """Null hypothesis: model A and model B are exchangeable on each test row
    (i.e. which one is 'A' vs 'B' for a given row is arbitrary). For each
    permutation, randomly swap each row's (pred_a, pred_b) label with 50%
    probability, recompute the macro-F1 difference, and see how often the
    permuted difference is as extreme as the one actually observed."""
    rng = np.random.default_rng(seed)
    observed = _macro_f1(y_true, pred_a) - _macro_f1(y_true, pred_b)
    n = len(y_true)
    count_as_extreme = 0
    for _ in range(n_perm):
        swap = rng.random(n) < 0.5
        perm_a = np.where(swap, pred_b, pred_a)
        perm_b = np.where(swap, pred_a, pred_b)
        diff = _macro_f1(y_true, perm_a) - _macro_f1(y_true, perm_b)
        if abs(diff) >= abs(observed):
            count_as_extreme += 1
    p_value = (count_as_extreme + 1) / (n_perm + 1)  # +1/+1: standard finite-permutation correction
    return {"observed_diff": float(observed), "p_value": float(p_value), "n_permutations": n_perm}


def run() -> dict:
    y_true, preds = _train_all()
    pairs = [
        ("logistic_regression", "rule_baseline"),
        ("logistic_regression", "xgboost"),
        ("logistic_regression", "random_forest"),
        ("xgboost", "rule_baseline"),
        ("random_forest", "rule_baseline"),
    ]
    results = {}
    for a, b in pairs:
        key = f"{a}_vs_{b}"
        results[key] = {
            "bootstrap": paired_bootstrap_ci(y_true, preds[a], preds[b]),
            "permutation": paired_permutation_test(y_true, preds[a], preds[b]),
        }
    return {
        "experiment_id": "significance_testing",
        "method": f"Paired bootstrap (n={N_BOOTSTRAP} resamples, 95% percentile CI) and paired permutation "
                  f"test (n={N_PERMUTATIONS} permutations) on macro-F1 differences, computed from a real "
                  f"retraining run (seed={SEED}, same hyperparameters as app/ai/train.py) on the fixed "
                  f"70/30 test split (n_test={len(y_true)}).",
        "point_estimates_macro_f1": {name: round(_macro_f1(y_true, p), 4) for name, p in preds.items()},
        "comparisons": results,
    }


def main() -> int:
    result = run()
    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "significance_testing.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Statistical significance testing: AI risk model comparison\n",
        result["method"] + "\n",
        "| comparison | observed diff | bootstrap 95% CI | excludes 0? | permutation p-value |",
        "|---|---|---|---|---|",
    ]
    for key, r in result["comparisons"].items():
        b, p = r["bootstrap"], r["permutation"]
        lines.append(
            f"| {key.replace('_', ' ')} | {b['observed_diff']:+.4f} | "
            f"[{b['ci95_low']:+.4f}, {b['ci95_high']:+.4f}] | "
            f"{'yes' if b['ci95_excludes_zero'] else 'no'} | {p['p_value']:.4f} |"
        )
    (out_dir / "significance_testing.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

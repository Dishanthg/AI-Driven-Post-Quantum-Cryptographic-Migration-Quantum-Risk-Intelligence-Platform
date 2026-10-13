# 09. AI Risk Experiments

SYNTHETIC DATA (`synthetic_crypto_inventory`, n=2000, seed=42) — labels are
a documented weighted formula with a withheld nonlinear interaction term
plus noise, **not** real organizational ground truth. All numbers below are
from a REAL, EXECUTED training run
(`backend/artifacts/models/risk_prioritization/20260904T055302Z/metadata.json`),
independently re-derivable via `make train`.

## Model comparison (macro-F1, n_test=600)
| Model | Macro-F1 | Macro-Precision | Macro-Recall | QW Kappa | Train time |
|---|---|---|---|---|---|
| Rule baseline | 0.7232 | 0.7577 | 0.7033 | 0.8444 | n/a (not trained) |
| **Logistic regression** | **0.7897** | 0.8018 | 0.7797 | 0.8807 | 0.085s |
| Random forest | 0.7709 | 0.7928 | 0.7545 | 0.8675 | 1.134s |
| XGBoost | 0.7349 | 0.7462 | 0.7259 | 0.8464 | 4.701s |

**The finding that mattered most:** the simplest model won, and the most
complex model (XGBoost) essentially tied the hand-written rule baseline.
Going in, the expectation was that XGBoost would clearly win — Rule 20 of
the project spec explicitly warns against assuming this, and the actual
data confirmed the warning was warranted, not just a formality.

## Ranking consistency (H1)
5-fold RandomForest retraining, pairwise Kendall's τ on a fixed holdout:
- ML fold-pairwise τ: mean 0.9317, min 0.9267 (high but not perfect
  self-consistency under resampling).
- Rule baseline: τ=1.0 by construction (deterministic, not retrained — not
  a fair "more consistent" comparison on its own).
- ML-vs-rule agreement: τ=0.8170.

## Ablation study (Section 40)
One feature removed at a time, logistic regression retrained and
re-evaluated (`research/tables/ablation_risk_features.md`):

| Removed feature | Macro-F1 | Δ vs. full |
|---|---|---|
| `internet_exposure_bin` | 0.4479 | **-0.3417** |
| `quantum_vulnerability_ord` | 0.5424 | -0.2472 |
| `data_sensitivity_ord` | 0.6483 | -0.1413 |
| `asset_criticality_ord` | 0.7029 | -0.0868 |
| `data_lifetime_years_norm` | 0.7696 | -0.0200 |
| `business_importance_ord` | 0.7756 | -0.0140 |
| (none — full set) | 0.7897 | 0.0000 |
| `key_size_norm` | 0.7999 | +0.0102 |
| `migration_complexity_ord` | 0.8059 | +0.0162 |

**Unplanned finding:** removing `key_size_norm` or `migration_complexity_ord`
*improved* macro-F1 slightly. Checking `app/ai/dataset.py::true_risk_score`
shows why — `migration_complexity` is never used in the synthetic label
formula at all, so it is pure noise to the model, and dropping noise
features acted as a mild regularizer. This was not anticipated and is
reported as found (see `research/RESEARCH_LOG.md` for the in-the-moment
record), not adjusted after the fact.

## Statistical significance testing (Section 41)
Point estimates alone don't say whether a macro-F1 gap is real or
resampling noise. `research/experiments/significance_testing.py` adds
paired bootstrap 95% CIs (n=2000 resamples) and paired permutation tests
(n=2000) on macro-F1 differences, from a real retraining run:

| comparison | observed diff | 95% CI | excludes 0? | permutation p |
|---|---|---|---|---|
| logistic regression vs. rule baseline | +0.0664 | [+0.033, +0.101] | yes | 0.0005 |
| logistic regression vs. XGBoost | +0.0547 | [+0.013, +0.096] | yes | 0.0105 |
| logistic regression vs. random forest | +0.0188 | [-0.017, +0.057] | no | 0.3473 |
| **XGBoost vs. rule baseline** | +0.0117 | [-0.039, +0.062] | **no** | **0.6592** |
| random forest vs. rule baseline | +0.0477 | [-0.003, +0.093] | no (borderline) | 0.0565 |

**This is the single most important statistical finding in the project.**
The point estimate suggested XGBoost narrowly beat the rule baseline
(0.735 vs. 0.723); the significance test shows that gap is statistically
indistinguishable from zero (p=0.659) — i.e., on this dataset, there is no
rigorous evidence that XGBoost outperforms a hand-written deterministic
rule at all. Only logistic regression's improvements are statistically
supported. This directly answers RQ3 with more precision than the point
estimates alone could: "can ML improve migration prioritization" has the
honest answer "yes, but specifically the simplest model tested, and not
with the complexity most people would reach for first."

## SHAP explainability
Verified end-to-end (`tests/test_ai_risk_engine.py::test_train_and_explain_end_to_end`):
`app/ai/explain.py` produces real per-asset SHAP attributions for tree
models (`shap.TreeExplainer`) and exact coefficient-based attributions for
logistic regression — never a hand-authored "top factors" string. See
`docs/architecture/adr/ADR-004-explainability.md`.

## What was not done
No hyperparameter search was performed for any of the three models — fixed,
documented hyperparameters were used throughout (see `06_methodology.md`).
It is possible a tuned XGBoost would outperform logistic regression; the
untuned comparison reported here is what was actually run, not a claim
about each algorithm's ceiling performance.

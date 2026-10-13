# 11. Ablation Studies

All four ablation types Section 40 asks for are now implemented and executed.

## 1. AI risk model feature ablation
`research/experiments/ablation_risk_features.py` removes one of the 8
risk-model features at a time and re-trains/re-evaluates logistic
regression, holding everything else fixed. Full results, including the
unplanned finding about `migration_complexity_ord` being pure label noise,
are in `09_ai_risk_experiments.md` and `research/tables/ablation_risk_features.md`.

Ranked by impact (most damaging removal first): `internet_exposure_bin`
(-0.342 macro-F1) > `quantum_vulnerability_ord` (-0.247) >
`data_sensitivity_ord` (-0.141) > `asset_criticality_ord` (-0.087) >
`data_lifetime_years_norm` (-0.020) > `business_importance_ord` (-0.014) >
`key_size_norm` (+0.010) > `migration_complexity_ord` (+0.016). This
ordering is directly consistent with the synthetic label formula's own
weights (`app/ai/dataset.py::LABEL_WEIGHTS`), which is a useful sanity
check that the ablation methodology measures what it claims to.

## 2. AI model ablation (systems-level, downstream impact)
`research/experiments/ablation_ai_model.py` runs the real
discover → assess → recommend → plan pipeline twice on the 42-asset lab —
once with risk assessment fed by the trained ML model, once by the rule
baseline — and measures downstream consequences.

**Result:** 3 of 42 assets (7.1%) receive a different PQC recommendation
strategy, and 2 migration plans receive a different priority, purely as a
consequence of which risk-assessment method fed the recommender. This is a
genuine, non-trivial finding distinct from Experiment 3's raw classifier
metrics: the model-vs-rule choice has real downstream operational
consequences for a meaningful minority of assets, not just an abstract
score difference.

**A real bug was found and fixed while building this ablation**: the first
version joined the two runs' results by `Asset.id`, which is a freshly
generated UUID per run and therefore never matches across two separate
database instances — the join silently matched nothing, producing a false
"0 changes" result that looked like a clean null finding. Caught by
noticing the migration-plan *counts* differed (16 vs. 18) despite the
(bogus) "0 recommendations changed" — a contradiction that shouldn't be
possible if truly nothing changed. Fixed by joining on `hostname` instead,
with an assertion that guards against the same failure mode recurring
silently. See `13_failures_and_lessons.md`.

## 3. Explainability layer ablation
`research/experiments/ablation_explainability.py` compares the platform's
real per-feature attribution (exact logistic-regression coefficients,
matching `app/ai/explain.py`) against a cheap, model-free heuristic (rank
features by |standardized value| from the population mean).

**Result:** mean top-3 Jaccard overlap only 0.425 (exact-match rate 10.5%),
full-ranking Spearman correlation only 0.104 — the real attribution method
disagrees substantially with the naive heuristic most of the time. This
supports keeping the real (SHAP/coefficient-based) explainability layer
rather than substituting a cheap approximation: the two methods are not
redundant.

## 4. PQC benchmark information ablation
`research/experiments/ablation_benchmark_info.py` runs the pipeline with
vs. without real benchmark data available to the recommendation engine.
This ablation was only meaningful because `app/recommendations/engine.py`
was extended this session to actually consult real `BenchmarkRun` data for
long-lived, internet-facing, TLS-certificate signature assets (a real gap
against design doc Section 24's "performance requirement" input — see
`ADR-005` and `16_technical_contributions.md`); before that change the
recommender never touched benchmark data at all, which would have made
this ablation trivially a no-op.

**Result:** 0 of 42 assets changed. Independently re-verified as a genuine
finding (not the same asset_id-join bug that affected ablation #2, which
was checked for and fixed pre-emptively in this script before it was ever
reported) by directly checking the lab YAML configs: no asset in the
current 42-asset lab meets the specific condition
(>10y lifetime + internet-facing + `tls_certificate` usage + still on a
classical signature algorithm) that the new logic checks for. This is a
real, reportable finding about the current lab data's coverage, not a
failure of the feature.

## Statistical rigor added alongside the ablations
`research/experiments/significance_testing.py` (Section 41, previously
NOT IMPLEMENTED) adds paired bootstrap 95% confidence intervals and paired
permutation tests to the model comparisons underlying ablation #1 and
Experiment 3. See `09_ai_risk_experiments.md` for the full results — the
headline finding is that XGBoost's apparent edge over the rule baseline
(a 0.012 point-estimate gap) is **not** statistically significant
(p=0.659), while logistic regression's wins over both the rule baseline
and XGBoost are (p=0.0005 and p=0.010 respectively).

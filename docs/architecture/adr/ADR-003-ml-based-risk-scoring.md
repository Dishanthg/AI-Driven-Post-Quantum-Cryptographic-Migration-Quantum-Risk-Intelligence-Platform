# ADR-003: ML-based risk scoring alongside (not instead of) a rule baseline

## Status
Accepted, implemented (`backend/app/ai/rule_baseline.py`,
`backend/app/ai/train.py`, `backend/app/ai/dataset.py`).

## Context
RQ3/H1 ask whether ML improves migration prioritization over static rules,
and Rule 20 of the design explicitly forbids assuming ML (or any specific
model) is automatically superior. That means the platform must implement
*both* approaches, evaluate them under the same metrics, and report the
result honestly even if the rule baseline wins on some axis — which,
in the real run recorded in `research/tables/risk_model_comparison.md`,
it very nearly does (macro-F1: rule 0.723 vs. XGBoost 0.735, both below
logistic regression's 0.790).

## Problem
No real enterprise cryptographic-migration ground truth exists (Section 60
lists this as an explicit limitation) — so what does "the model predicts
priority" even mean without fabricating labels, and how do we avoid the
label construction being circular (i.e. secretly encoding the rule baseline's
own logic into the "ground truth")?

## Alternatives considered
- **Skip the baseline, report only ML metrics.** Rejected — directly
  violates Rule 20 and RQ3, which is specifically a *comparative* question.
- **Make the synthetic label a linear function identical in form to the rule
  baseline.** Rejected — this would make "ML beats the rule" true by
  construction (the rule baseline is deliberately withheld from seeing the
  label formula), which is scientifically empty. See `dataset.py`'s
  `DATASET_CARD` docstring.
- **Use only one ML model (e.g. XGBoost) as "the" ML approach.** Rejected —
  Section 20 requires comparing at least LogReg/RandomForest/XGBoost, since
  assuming gradient boosting wins by default is exactly the un-earned
  assumption Rule 20 warns against, and the actual run confirms XGBoost is
  *not* the best performer here.

## Decision
- `app/ai/dataset.py` generates a SYNTHETIC (explicitly labeled as such)
  inventory whose ground-truth priority is a documented weighted sum over
  quantum vulnerability, asset criticality, data sensitivity, data lifetime,
  internet exposure, and business importance, **plus a nonlinear interaction
  term** (`internet_exposure × data_sensitivity`) and Gaussian noise
  (`NOISE_STD=0.06`) — deliberately withheld from the rule baseline, so that
  "can ML recover structure a linear heuristic misses" is a falsifiable
  question rather than a foregone conclusion.
- `app/ai/rule_baseline.py` is a separate, simpler, linear scorer — the kind
  a real organization could plausibly hand-write — with no access to the
  label formula or its interaction term.
- `app/ai/train.py` trains and evaluates LogisticRegression, RandomForest,
  and XGBoost against the same train/test split (`random_state=42`,
  `stratify=y`), reporting macro-F1/precision/recall and quadratic-weighted
  kappa for all four approaches (including the rule baseline) side by side.
- `app/ai/model_registry.py` records every trained version with its metrics,
  dataset reference, and seed for reproducibility (Section 56).

## Consequences
- Positive: the comparison is real and was allowed to come out
  inconveniently close (logistic regression: 0.790 macro-F1; rule baseline:
  0.723) — no result was adjusted to make ML look better.
- Positive: `research/tables/risk_model_comparison.md` and
  `research/figures/risk_model_comparison.png` are generated directly from
  `metadata.json` (`research/generate_report_assets.py`) — the table cannot
  drift from what was actually trained.
- Negative / limitation: the label itself is synthetic. The comparison
  answers "can these models recover a documented synthetic construction,"
  not "does this predict real migration urgency" — stated explicitly in
  `dataset.py`'s docstring and repeated in the Master's-application
  evidence package rather than left implicit.

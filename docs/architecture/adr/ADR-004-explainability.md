# ADR-004: SHAP-based explainability for the ML risk model

## Status
Accepted, implemented (`backend/app/ai/explain.py`), verified
(`backend/tests/test_ai_risk_engine.py::test_train_and_explain_end_to_end`).

## Context
Section 22 requires every risk score to be shown with its top contributing
factors, and the rule baseline is transparent by construction (its score is
a literal weighted sum you can print). An opaque ML prediction without a
per-asset explanation would fail that requirement and would also make it
impossible to sanity-check whether the model is picking up the intended
signal (e.g. "internet-exposed + high-sensitivity" interaction) or something
spurious.

## Problem
How do we produce a genuine, per-prediction, per-feature explanation for
tree ensembles (RandomForest, XGBoost) and linear models (LogisticRegression)
without hand-authoring a "top factors" string that isn't actually derived
from the model's decision — which would violate Rule 12 ("every AI
prediction must be reproducible") by making the explanation unfalsifiable.

## Alternatives considered
- **Hand-written heuristic explanation** (e.g. "high risk because internet
  exposure"), independent of what the model actually weighted. Rejected —
  this is not an explanation of the model, it's a second, undeclared rule
  engine wearing the ML model's confidence score.
- **Permutation importance only (global, not per-asset).** Rejected — Section
  22 asks for a per-asset "why is *this* asset scored this way," which
  requires a local explanation method, not a single global ranking.
- **LIME.** Considered; SHAP was preferred because it has closed-form exact
  solutions for tree ensembles (`TreeExplainer`) and linear models, giving
  deterministic, reproducible attributions rather than LIME's local
  perturbation-sampling approximation.

## Decision
`app/ai/explain.py`'s `RiskExplainer` loads the currently active trained
model artifact and:
- For tree models: computes real SHAP values via `shap.TreeExplainer` for
  the predicted class, handling both the older (list-of-arrays) and newer
  (stacked 3D array) SHAP output shapes.
- For LogisticRegression: uses the model's own coefficients times the scaled
  feature vector — an exact, not approximate, per-feature contribution for a
  linear model (SHAP would reduce to this analytically anyway for a linear
  model with independent features).
- Returns the top-3 contributing features by absolute magnitude, alongside
  the risk score, priority, and model confidence — surfaced verbatim by the
  `/api/v1/risk` endpoints and the risk-explanation UI, never re-authored.

## Consequences
- Positive: explanations are reproducible — same model artifact + same
  feature vector always yields the same attribution (verified in
  `test_train_and_explain_end_to_end`).
- Positive: the same module works across model classes without a
  per-algorithm bespoke explanation writer.
- Negative: SHAP attribution for tree ensembles is exact but computationally
  heavier than the rule baseline's O(1) weighted sum — acceptable at
  QuantumShield's per-asset, on-demand call pattern, but not benchmarked at
  bulk-inventory scale (noted as a scaling limitation, not measured).

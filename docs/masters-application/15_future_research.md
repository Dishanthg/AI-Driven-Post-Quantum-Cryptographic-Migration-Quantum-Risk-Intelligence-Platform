# 15. Future Research

Ordered roughly by how directly each extends work already done in this
project, not by importance.

## Near-term extensions (would directly close gaps in `14_limitations.md`)
- **Model-choice, explainability-layer, and benchmark-information
  ablations** (Section 40's remaining three, beyond the feature ablation
  already done).
- **Statistical significance testing** on model-comparison differences —
  e.g. bootstrap or paired-permutation tests on the macro-F1 gap between
  logistic regression and the rule baseline, across multiple seeds, rather
  than single point estimates.
- **Hyperparameter search** for RandomForest/XGBoost, to check whether the
  logistic-regression win in Experiment 3 survives tuning or is an
  artifact of untuned defaults.
- **Extend noise analysis (Experiment 8) to the Shor lab**, and to
  additional noise model shapes (e.g. amplitude damping, crosstalk).
- **Exercise the PostgreSQL deployment path in CI**, not just SQLite.

## Medium-term research directions
- **Real (or realistically messy) inventory data.** Even without a real
  organization's cooperation, a more adversarial synthetic-inventory
  generator — malformed configs, ambiguous algorithm identifiers,
  conflicting sources — would stress-test the discovery scanner beyond
  this project's clean, hand-authored lab configs (RQ1).
- **Hybrid signature composition**, extending `HybridCryptoProvider` beyond
  KEM-only, and benchmarking it alongside the existing hybrid KEM row.
- **Calibrated noise models** using published device characterization data
  (e.g. from IBM Quantum's public backend properties) rather than
  illustrative rates, to make Experiment 8's noise comparison more
  representative of a specific real device class.
- **A genuine algorithm-classification-only baseline** for H2, to make that
  hypothesis's evidence as direct as H5's (currently inferred from the
  ablation rather than from a dedicated baseline model).

## Longer-term, more open questions
- **Real quantum hardware execution** of the Grover/Shor labs at their
  current (still-small) scale, once hardware access is available, as a
  genuine ideal-vs-noisy-vs-real three-way comparison rather than the
  current ideal-vs-simulated-noise two-way one.
- **Longitudinal migration-effort validation** — if this platform (or a
  descendant of it) were ever used to plan and track a real migration,
  comparing the deterministic effort formula's estimates against actual
  hours spent would be the first real calibration data this project has
  never had access to.
- **Standards evolution tracking.** As NIST's PQC standards portfolio
  evolves (e.g. additional signature schemes beyond the initial three),
  extending the `AlgorithmRegistry` and benchmark suite to track new
  standardized algorithms without architectural rework — a live test of
  whether the `CryptoProvider`/registry design (Experiment 6's subject)
  holds up against a real external-standard change, not just an internal
  algorithm swap.
- **Adversarial robustness of the AI risk model** — e.g. whether an
  attacker who can influence input asset metadata (data sensitivity
  labels, criticality tags) could manipulate migration prioritization
  downward for a target asset; not investigated at all in this project.

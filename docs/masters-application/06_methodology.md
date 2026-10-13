# 06. Methodology

## General principles applied throughout
- **No fabricated numbers.** Every risk score, benchmark value, and
  quantum-lab result is produced by executing real code at report-generation
  time; `research/generate_report_assets.py` explicitly skips (rather than
  invents) any figure/table whose prerequisite artifact is missing.
- **Reproducibility.** Every stochastic process (synthetic dataset
  generation, train/test splitting, model training, quantum-simulator
  shots) is seeded (`seed=42` throughout) and documented inline.
- **Explicit data provenance labeling.** REAL / SYNTHETIC / SIMULATED is
  stated in module docstrings, dataset cards, and (in the frontend) UI copy
  — never left to be inferred.
- **Baselines before claims.** Every "AI/ML does X better" question is
  investigated against a deterministic baseline built first, without access
  to whatever advantage the ML approach might have (e.g. the rule baseline
  never sees the synthetic label's nonlinear interaction term).

## Benchmark methodology (Experiments 1/2)
`backend/app/benchmarks/engine.py` runs each operation (keygen,
encapsulate, decapsulate, sign, verify) `ITERATIONS=30` times per
algorithm (with an unmeasured warmup pass first), recording per-call
wall-clock timing via `time.perf_counter()`. Reported statistics: mean,
median, standard deviation, p95/p99, and a bootstrap 95% confidence
interval. Public key / ciphertext / signature sizes are read directly off
the real generated key/ciphertext/signature bytes, never looked up from a
spec table. Environment metadata (captured per run) includes the fields
listed in `BenchmarkSummaryOut.environment`.

## AI risk model methodology (Experiment 3)
`app/ai/dataset.py` generates `n=2000` synthetic assets with a documented
weighted-sum label formula plus an explicit nonlinear interaction term
(`internet_exposure × data_sensitivity`) and Gaussian noise (σ=0.06),
discretized into 4 priority classes via fixed thresholds. A 70/30
stratified train/test split (`random_state=42`) is used throughout. Three
classifiers (LogisticRegression, RandomForestClassifier, XGBClassifier) are
trained with fixed, documented hyperparameters (see `app/ai/train.py`) and
evaluated on the same held-out split as the rule baseline, using macro-F1,
macro-precision/recall, and quadratic-weighted Cohen's kappa. A separate
5-fold ranking-consistency check (Kendall's τ) evaluates RandomForest
stability under resampling against a fixed evaluation set.

## Quantum lab methodology (Experiments 7/8)
Grover: builds an oracle + diffuser circuit for a given marked-state set,
runs the theoretically optimal number of iterations
(`round((π/4)·√(N/M))`), executes on `qiskit_aer.AerSimulator` (statevector/
qasm simulation, not hardware), and reports measured success probability
over the requested shot count. Shor: implements quantum phase estimation
over modular exponentiation with a classically-computed continued-fractions
period extraction, restricted to small composite `N` values by the
`quantum_max_qubits` cap. Noise analysis (Experiment 8) adds a depolarizing
(gate) + readout-error noise model to the same Grover circuit and compares
ideal vs. noisy success probability at fixed shots/seed.

## Ablation methodology (Section 40)
`research/experiments/ablation_risk_features.py` retrains a single fixed
model (logistic regression, the best full-feature performer) with exactly
one feature removed at a time, holding the train/test split, seed, and all
other hyperparameters constant, and reports the macro-F1 delta versus the
full-feature model.

## What was NOT done methodologically (stated plainly)
No statistical significance testing (e.g. paired bootstrap CIs on the
macro-F1 differences between models) was performed — the comparisons in
this project report point estimates from single seeded runs, not confidence
intervals on the *differences* between models. This is recorded as a
methodological gap in `14_limitations.md`, not glossed over.

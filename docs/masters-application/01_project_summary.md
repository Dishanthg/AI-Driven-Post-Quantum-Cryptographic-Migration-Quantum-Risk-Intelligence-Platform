# 01. Project Summary

**QuantumShield** is an AI-assisted platform for cryptographic asset
discovery, quantum-risk assessment, and post-quantum migration planning. It
was built to investigate one applied question at the intersection of
quantum computing, cryptography, cybersecurity, and machine learning: how
can an organization find out what cryptography it actually runs, estimate
how exposed each use is to future quantum attacks, and decide what to do
about it — without hand-waving the parts of that pipeline that are easy to
fake (risk scores, benchmark numbers, "our AI is 95% accurate" claims,
quantum demos that quietly imply more than they show)?

## What was actually built (all VERIFIED unless noted)
- **Cryptographic inventory & discovery.** A scanner that reads a
  controlled, synthetic 8-service "enterprise lab" (`backend/enterprise_lab/`,
  42 assets) and populates a ~20-entity relational schema (Alembic-migrated,
  SQLite for dev/test, PostgreSQL-shaped for `docker-compose.yml` — see
  `docs/architecture/adr/ADR-002-postgresql.md`).
- **Algorithm registry & quantum threat model.** An extensible classification
  of classical and standardized PQC algorithms (ML-KEM/ML-DSA/SLH-DSA per
  FIPS 203/204/205), paired with a static, citation-backed reference table
  explaining Shor's and Grover's algorithms' implications — deliberately
  never claiming real keys have been or can be broken (see
  `backend/app/quantum/threat_model.py`).
- **CryptoProvider abstraction** (Classical / PQC / Hybrid) — real,
  roundtrip-verified implementations over `cryptography` and `pqcrypto`,
  never a from-scratch primitive (`docs/architecture/adr/ADR-001-*`).
- **Quantum labs.** Real Grover and Shor simulations on Qiskit Aer, hard-
  capped at 16 qubits so the labs are structurally incapable of touching a
  cryptographically relevant key space (`ADR-006`), plus a real ideal-vs-
  noisy comparison (Experiment 8).
- **AI risk engine.** A documented synthetic dataset with a withheld
  nonlinear interaction term, a rule-based baseline, and three trained
  classifiers (LogReg/RandomForest/XGBoost) compared honestly — the simplest
  model (logistic regression, macro-F1 0.790) beat both the rule baseline
  (0.723) and XGBoost (0.735), which was not the expected outcome going in
  (`ADR-003`, `research/RESEARCH_LOG.md`). SHAP-based per-asset
  explainability (`ADR-004`).
- **Recommendation, planning, and migration simulation.** A deterministic,
  explainable recommendation engine; a migration planner with a documented
  effort-estimation formula; a simulator that actually benchmarks and
  roundtrip-verifies each migration stage.
- **Cryptographic agility demonstration.** A real measurement (Experiment 6)
  that swapping a sample service's signing algorithm through
  ECDSA-P256 → ML-DSA-65 → SLH-DSA-SHA2-128F changes **zero** lines in its
  business logic (verified by file-hash equality across three real swaps),
  versus 4 hard-wired call sites in a tightly-coupled comparison version.
- **Benchmarking.** A real timing harness (bootstrap CIs, percentiles) run
  against 13 algorithms/compositions (`research/tables/benchmark_sweep.csv`).
- **Full API + auth + RBAC + audit logging** (FastAPI, JWT, 3 roles, 11
  routers) and a **React/TypeScript frontend** wired to the live API with no
  mocked data (13 pages).
- **66/66 backend tests passing**, `ruff check` clean, CI wired
  (lint + full test suite + `pip-audit` on every push/PR).

## What this project is not
It is not a claim that RSA/ECC has been broken, that quantum computers can
currently threaten deployed cryptography, or that the AI risk model reflects
validated real-world ground truth (it does not — the training data is
synthetic and explicitly labeled as such throughout). See
`14_limitations.md` for the full, unhedged list.

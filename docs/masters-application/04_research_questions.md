# 04. Research Questions

Primary: *How can AI-assisted cryptographic asset discovery and risk-aware
migration planning accelerate organizational transition toward post-quantum
cryptography while balancing security, computational overhead,
compatibility and operational risk?*

| # | Question | Status in this project |
|---|---|---|
| RQ1 | How accurately can a system discover and classify cryptographic assets across heterogeneous applications? | Answered for the controlled lab scope: `discovery/scanner.py` correctly imports all 42 assets across 8 YAML-configured services with 0 classification errors in the current lab configs (verified by `tests/test_discovery_scanner.py`). Not evaluated against real-world heterogeneous, messy configuration data (see limitations). |
| RQ2 | How can quantum-vulnerability risk be quantified using cryptographic, asset and business characteristics? | Answered via a documented, weighted, feature-based formula (rule baseline) and via a trained classifier over the same feature space (ML risk engine) — both implemented and compared. Not validated against real incident/migration-urgency ground truth, because none exists for this project (explicit limitation). |
| RQ3 | Can machine learning improve migration prioritization compared with static rule-based approaches? | Tested (Experiment 3). Answer, honestly reported: **mixed, model-dependent**. Logistic regression outperformed the rule baseline (macro-F1 0.790 vs. 0.723); XGBoost, despite being the more complex model, did **not** clearly outperform the rule baseline (0.735 vs. 0.723). See `12_results.md`. |
| RQ4 | What are the performance trade-offs between classical and standardized post-quantum algorithms? | Answered with real benchmark data across 13 algorithms/compositions — see `08_pqc_experiments.md`. |
| RQ5 | What performance and compatibility costs are introduced by hybrid cryptographic migration? | Partially answered — the hybrid ECDH+ML-KEM-768 composition is benchmarked as its own provider (`research/tables/benchmark_sweep.csv`), showing measurable overhead over either primitive alone. Hybrid *signatures* were not implemented (explicit scope limitation), so this is answered for hybrid key exchange only. |
| RQ6 | How can cryptographic agility reduce migration complexity? | Tested directly (Experiment 6): 0 business-logic code changes across 3 real algorithm swaps under the `CryptoProvider` abstraction, vs. 4 documented hard-wired call sites in a tightly-coupled comparison design. |
| RQ7 | How can quantum-computing simulations improve understanding of cryptographic risk without overstating practical quantum capabilities? | Addressed structurally (hard qubit caps, mandatory SIMULATION/hardware labeling, `ADR-006`) and empirically (Experiment 8's ideal-vs-noisy comparison shows *why* current hardware is far from the threat model Shor's algorithm describes at scale). |

See `research/RESEARCH_LOG.md` for the full chronology and
`research/tables/` for the underlying data behind every "tested" row above.

# 12. Results

Cross-experiment synthesis. Each row links to the detailed doc.

| Experiment | Headline real result | Detail |
|---|---|---|
| 1/2: PQC benchmarking | PQC keygen often *faster* than RSA (ML-KEM-512: 0.098ms vs. RSA-2048: 200ms); PQC signatures up to ~244x larger than ECDSA (SLH-DSA-SHA2-128F: 17,088B vs. ECDSA-P256: 70B) | `08_pqc_experiments.md` |
| 3: AI risk prioritization | Logistic regression (macro-F1 0.790) beat both the rule baseline (0.723) and XGBoost (0.735) — the simplest model won | `09_ai_risk_experiments.md` |
| 4: AI vs. rule-based ranking | ML self-consistency under resampling: τ=0.932; ML-vs-rule agreement: τ=0.817 — real but imperfect consistency, no clean "winner" declared | `05_hypotheses.md` (H1) |
| 5: Hybrid crypto | Hybrid ECDH+ML-KEM-768 encapsulate costs ~4x ML-KEM-768 alone (1.01ms vs. 0.25ms) — real composition overhead, KEM only | `08_pqc_experiments.md` |
| 6: Crypto agility | 0 business-logic lines changed across 3 real algorithm swaps (provider-abstracted) vs. 4 hard-wired call sites (tightly coupled) | `05_hypotheses.md` (H5), `research/tables/exp6_crypto_agility.md` |
| 7: Quantum lab | Grover: 96%+ measured success probability at theoretical-optimal iterations; Shor: correctly factored 15 and 21 | `07_quantum_experiments.md` |
| 8: Noise analysis | Grover success probability collapses 96%→44% under modest (0.1-2%) per-gate/readout noise | `07_quantum_experiments.md` |
| Feature ablation | `internet_exposure_bin` most important feature (-0.342 macro-F1 if removed); `migration_complexity_ord` is pure noise to the model (+0.016 if removed) | `11_ablation_studies.md` |
| AI-model ablation (systems-level) | 3/42 assets (7.1%) get a different PQC recommendation depending on ML-vs-rule risk assessment; 2 migration plans change priority | `11_ablation_studies.md` |
| Explainability ablation | Real attribution vs. cheap heuristic: top-3 Jaccard 0.425, exact-match 10.5%, Spearman 0.104 — the real method isn't redundant with a naive one | `11_ablation_studies.md` |
| Benchmark-info ablation | 0/42 assets changed — verified as a genuine finding (no lab asset meets the condition the new logic checks), not a bug | `11_ablation_studies.md` |
| Significance testing | XGBoost's edge over the rule baseline is **not** statistically significant (p=0.659); logistic regression's wins over the rule baseline (p=0.0005) and XGBoost (p=0.010) are | `09_ai_risk_experiments.md` |
| Migration pipeline | 42-asset lab → 32 migration plans, 1183 estimated hours (SQLite run) / 16 plans, 591.5 hours (a later, smaller Postgres verification run reflecting fewer actionable recommendations that run) — fully re-derivable formula per plan | `10_migration_experiments.md` |
| PostgreSQL verification | Real Alembic migration + full demo pipeline run against Postgres; caught and fixed a real `VARCHAR(32)`-too-narrow bug SQLite silently allowed | `13_failures_and_lessons.md`, `docs/architecture/adr/ADR-002-postgresql.md` |

## What "results" means here
Every number above traces to a specific script, artifact, or test that can
be re-run (`Makefile` targets: `benchmark`, `train`, `quantum-lab`, `exp6`,
`ablation`, `ai-model-ablation`, `explainability-ablation`,
`benchmark-info-ablation`, `significance`, `noise-analysis`,
`migration-demo`). None of these numbers were typed in by hand as a target
to hit — several came out differently than expected (XGBoost not winning,
and *not statistically distinguishable* from the rule baseline;
`migration_complexity_ord` being noise; two ablation scripts' first drafts
silently producing a false "0 changes" from a join bug) and are reported
as found. See `13_failures_and_lessons.md` for the expectations that were
*not* met and what that means.

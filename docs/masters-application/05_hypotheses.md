# 05. Hypotheses

Per the project's own rules, hypotheses were investigated, not assumed true.
Two came back genuinely mixed or partially disconfirmed — that is reported
here exactly as found, not adjusted.

## H1 — "AI-assisted risk prioritization provides more consistent migration prioritization than static rule-based prioritization."
**Status: partially supported, with an important caveat.** The rule
baseline is *trivially* self-consistent (Kendall's τ = 1.0 across "folds")
because it is a fixed deterministic formula, never retrained — that is not
a meaningful comparison point on its own. The more informative measurement
is the ML model's own stability under resampling: RandomForest's fold-
pairwise ranking consistency across 5 independently-trained folds was
τ = 0.932 (min 0.927) — high, but not perfect, meaning the ML ranking does
shift somewhat with which training sample it saw. Agreement between the
ML model and the rule baseline's rankings was τ = 0.817. **Interpretation:**
the ML model is reasonably, not perfectly, consistent, and it is a genuine
open question whether 0.93 self-consistency is "more consistent" than a
human-auditable static rule in a context where auditability itself has
value — this project reports the numbers rather than declaring a winner.
**Update (statistical significance testing):** a paired bootstrap/permutation
test (`research/experiments/significance_testing.py`) shows logistic
regression's macro-F1 improvement over the rule baseline is statistically
significant (95% CI [+0.033, +0.101], p=0.0005) — but XGBoost's smaller
improvement over the rule baseline is **not** (CI includes 0, p=0.659). So
H1's support is model-specific: the *best* ML model tested does
significantly outperform the rule baseline; a more complex model
(XGBoost) does not, despite a superficially positive point estimate. A
systems-level ablation (`ablation_ai_model.py`) additionally shows this
choice has real downstream consequences: 7.1% of assets get a different
PQC recommendation depending on which risk-assessment method is used.

## H2 — "Cryptographic inventory combined with asset criticality provides better migration prioritization than cryptographic algorithm classification alone."
**Status: supported by design, not independently ablated as a standalone
claim.** The ablation study (`research/tables/ablation_risk_features.md`)
shows `asset_criticality_ord` removal costs macro-F1 0.087 (0.790 → 0.703)
— substantial, confirming criticality carries real signal beyond algorithm
identity alone. A dedicated "algorithm-only" baseline model was not built
separately; this conclusion is inferred from the ablation rather than from
a head-to-head baseline comparison, which is a gap worth closing in future
work.

## H3 — "Post-quantum cryptographic algorithms introduce measurable computational and communication overhead compared with classical alternatives."
**Status: supported, but not uniformly in the "PQC is slower/bigger"
direction.** ML-KEM-512/768/1024 keygen is actually *faster* than RSA-2048/
3072 in the real benchmarks (e.g. ML-KEM-512 keygen ≈0.098ms vs. RSA-2048
≈200ms). Signature *sizes* tell the opposite story: SLH-DSA-SHA2-128f
signatures are 17,088 bytes vs. ECDSA-P256's 70 bytes — a ~244x increase.
The honest finding is "PQC overhead is real and algorithm-specific, not a
single uniform direction" — see `08_pqc_experiments.md` for the full table.

## H4 — "Hybrid cryptographic configurations can provide a transitional migration strategy with different security/performance trade-offs."
**Status: supported for hybrid key exchange.** The ECDH+ML-KEM-768 hybrid
provider is real, benchmarked, and roundtrip-verified, with measurably
higher combined cost than either primitive alone (encapsulate ≈1.01ms vs.
ML-KEM-768 alone ≈0.25ms). No security *proof* is claimed for the HKDF
composition (Rule 25) — this is an engineering trade-off measurement, not a
cryptographic security argument.

## H5 — "Cryptographic agility reduces simulated migration effort compared with tightly coupled cryptographic implementations."
**Status: supported, directly measured (Experiment 6).** 0 business-logic
code edits across 3 real algorithm swaps vs. 4 documented hard-wired call
sites in the tightly-coupled comparison file. This is the hypothesis with
the cleanest, least ambiguous supporting evidence in the project.

## H6 — "Quantum algorithm simulations can provide useful educational/security insights into theoretical attack complexity, while remaining computationally infeasible for realistic cryptographic key sizes on classical simulators."
**Status: supported by construction and by measurement.** The qubit cap
(`ADR-006`) makes the "infeasible at real key sizes" half true by
architecture, not just observation. The "useful insight" half is supported
by Experiment 8: a real, substantial noise-driven Grover success-
probability collapse (96% → 44%) is exactly the kind of concrete,
non-hand-wavy insight a small-scale simulation can honestly provide.

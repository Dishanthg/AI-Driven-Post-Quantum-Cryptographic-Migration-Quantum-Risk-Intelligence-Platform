# 17. Architecture Decisions

Full ADRs live in `docs/architecture/adr/` — this is an index with the
one-line "why" for each, for readers who want the summary before the detail.

| ADR | Decision | One-line why |
|---|---|---|
| [ADR-001](../architecture/adr/ADR-001-crypto-provider-abstraction.md) | `CryptoProvider` abstraction (Classical/PQC/Hybrid) | Makes crypto-agility (H5) a testable property instead of a slogan — business logic never imports a crypto library directly. |
| [ADR-002](../architecture/adr/ADR-002-postgresql.md) | PostgreSQL for docker-compose, SQLite for dev/test | Matches the ~20-entity relational schema's real needs (JSONB, FKs) while keeping the local dev loop dependency-free. |
| [ADR-003](../architecture/adr/ADR-003-ml-based-risk-scoring.md) | ML risk scoring alongside (never instead of) a rule baseline | RQ3/Rule 20 require an honest comparison — and the comparison came out close, which is only informative if both sides were actually built. |
| [ADR-004](../architecture/adr/ADR-004-explainability.md) | SHAP-based explainability | A risk score without a real per-feature attribution isn't reproducible (Rule 12) or auditable (Section 22). |
| [ADR-005](../architecture/adr/ADR-005-hybrid-migration-simulation.md) | Hybrid classical+PQC as a first-class, benchmarked strategy | RQ5/H4 require hybrid to be measured, not merely mentioned — and its cost profile is genuinely distinct from either primitive alone. |
| [ADR-006](../architecture/adr/ADR-006-quantum-simulation-scope.md) | Hard-capped, structurally-enforced quantum lab scope | The single highest-stakes integrity decision in the project — makes "cannot touch real key sizes" a code guarantee, not a docstring promise. |
| [ADR-007](../architecture/adr/ADR-007-deterministic-migration-authorization.md) | RBAC-gated, deterministic migration actions; no LLM in the authorization path | Section 51 requires this boundary to exist *before* any future LLM-assisted explanation layer is even considered. |

## How these decisions relate to each other
ADR-001 (agility) and ADR-006 (quantum scope) are the two decisions that
most directly encode this project's research integrity rules into
executable code rather than documentation alone — both use "the system
fails loudly if misused" as the enforcement mechanism (a `ValueError` for
qubit overflow; a testable file-hash equality for "zero code changes")
instead of relying on a developer reading a comment. ADR-003/ADR-004
together are what make the AI risk engine's claims falsifiable rather than
asserted — a model comparison without a baseline (ADR-003) or without
per-prediction attribution (ADR-004) would each individually undermine
Rule 12/20's reproducibility requirement. ADR-007 is forward-looking: no
LLM currently sits in QuantumShield's runtime decision path at all, but the
authorization boundary it describes is what any future LLM-assisted
feature would have to respect.

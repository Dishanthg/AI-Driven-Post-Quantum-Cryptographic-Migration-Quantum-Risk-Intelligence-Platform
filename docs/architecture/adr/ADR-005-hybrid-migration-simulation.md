# ADR-005: Hybrid classical+PQC as a first-class, simulated transitional strategy

## Status
Accepted, implemented (`backend/app/crypto/providers.py::HybridCryptoProvider`,
`backend/app/recommendations/engine.py`, `backend/app/migration/simulator.py`).

## Context
RQ5/H4 ask what a hybrid classical+PQC configuration costs and whether it's a
useful transitional strategy — a live debate in real PQC migration guidance
(e.g. hybrid TLS key exchange as a hedge against both "classical breaks
first" and "the new PQC scheme has an unforeseen flaw"). The design forbids
overclaiming security guarantees for hybrid schemes (Section 25) while still
requiring the platform to model and measure them.

## Problem
Where does "hybrid" fit relative to `pqc_migration` and `deferred`, and how
is its cost actually measured rather than asserted?

## Alternatives considered
- **Treat hybrid as just another target algorithm in the same list as
  ML-KEM-768.** Rejected — hybrid has a distinct cost/compatibility profile
  (runs both primitives, larger combined key material) and a distinct
  strategic role (transitional hedge, not a destination), so it needs to be
  a distinct recommendation `strategy` value, not folded into
  `pqc_migration`.
- **Model hybrid signatures too.** Rejected for this iteration — no
  standardized hybrid signature composition was implemented; only hybrid KEM
  (ECDH + ML-KEM-768 via HKDF) exists. Recommendation logic in
  `recommendations/engine.py` only offers `hybrid_migration` for
  key-exchange-shaped usage, where `HybridKEMProvider` actually exists —
  it does not claim hybrid signature support it doesn't have.
- **Estimate hybrid overhead analytically (sum of the two primitives' known
  costs) instead of benchmarking the composed provider directly.** Rejected
  — Rule 9/11 require real execution; `HybridCryptoProvider` is benchmarked
  as its own provider (`HYBRID-ECDH-ML-KEM-768` row in
  `research/tables/benchmark_sweep.csv`) so any HKDF/composition overhead is
  captured, not assumed away.

## Decision
- `HybridCryptoProvider` actually performs classical ECDH *and* ML-KEM-768
  encapsulation and combines both shared secrets through HKDF — not a
  concatenation or a stub.
- The recommendation engine can output `hybrid_migration` as a distinct
  strategy, with its own rationale/assumptions/tradeoffs text, separate from
  `pqc_migration`.
- The migration simulator benchmarks and roundtrip-verifies each stage a
  hybrid plan actually schedules; for `hybrid_migration` plans, a later
  full-PQC stage is explicitly described as future/unscheduled rather than
  silently simulated as if it had already happened.

## Consequences
- Positive: Experiment 5's classical-vs-PQC-vs-hybrid comparison
  (`research/tables/benchmark_sweep.csv`, `HYBRID-ECDH-ML-KEM-768` row) is
  measured from one consistent provider abstraction, not three different
  code paths.
- Negative: hybrid is KEM-only; hybrid signatures remain a documented gap,
  not a silent omission.
- Explicit non-claim: nothing in this codebase asserts a security proof for
  the HKDF-combined hybrid secret; it is presented as an engineering
  composition with measured performance characteristics, per Rule 25's
  prohibition on unsupported security guarantees.

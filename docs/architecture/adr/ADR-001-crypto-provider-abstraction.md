# ADR-001: CryptoProvider abstraction for cryptographic agility

## Status
Accepted, implemented (`backend/app/crypto/providers.py`, `backend/app/crypto/registry.py`).

## Context
QuantumShield's core research claim (H5, RQ6) is that cryptographic agility —
the ability to swap an algorithm without rewriting business logic — reduces
migration effort. That claim is untestable if the platform's own code
imports `cryptography` or `pqcrypto` directly wherever it signs, verifies, or
key-exchanges. We needed a design where "migrate an application from ECDSA to
ML-DSA" is demonstrably a configuration change, not a code change, so the
crypto-agility experiment (Experiment 6) measures something real rather than
an assertion.

## Problem
Where does the abstraction boundary go, and how thin can it be while still
covering classical, standardized-PQC, and hybrid classical+PQC operations
with one interface?

## Alternatives considered
- **No abstraction; call `cryptography`/`pqcrypto` at each call site.**
  Simplest to write, but makes crypto-agility a slogan rather than a testable
  property — there is nothing to point at as "the config changed, the code
  didn't."
- **Abstract only key exchange (KEM), leave signatures direct.** Rejected —
  the platform needs to benchmark and migrate signature-shaped assets
  (certificates, ML-DSA/SLH-DSA) with the same rigor as KEM-shaped ones.
- **Full provider-per-protocol (TLS-specific, cert-specific abstractions).**
  Rejected as premature — QuantumShield simulates migration effects rather
  than terminating real TLS connections; a lower-level primitive interface
  (keygen/encapsulate/decapsulate/sign/verify) is sufficient and simpler to
  reason about and benchmark uniformly.

## Decision
Define a single `CryptoProvider` interface (`KeyPair` + keygen/encapsulate/
decapsulate/sign/verify, with `supports_kem`/`supports_sign` capability
flags) and three implementations:
- `ClassicalCryptoProvider` — wraps `cryptography` (pyca) for RSA, ECDSA,
  ECDH, DH.
- `PQCProvider` — wraps `pqcrypto` (PQClean reference builds) for
  ML-KEM-512/768/1024, ML-DSA-44/65/87, SLH-DSA-SHA2-128f.
- `HybridCryptoProvider` — composes classical ECDH with ML-KEM-768 via HKDF,
  for KEM-shaped usage only (no hybrid signature composition is implemented).

Every provider is looked up by a string key (`get_provider(provider_key)`)
sourced from the `AlgorithmRegistry`. The benchmark engine, migration
simulator, recommendation engine, and the standalone crypto-agility demo
(`backend/agility_demo/`) all depend only on this interface — never on the
underlying libraries. No cryptographic primitive is implemented from scratch
(project Rule 6): classical operations use the audited `cryptography`
library; PQC operations use `pqcrypto`'s PQClean-derived implementations of
the FIPS 203/204/205 standards.

## Consequences
- Positive: `app/migration/simulator.py` can "migrate" an asset by calling
  `get_provider(target_key)` instead of `get_provider(current_key)` —
  Experiment 6 measures this literally (lines/files touched, config diff) in
  `backend/agility_demo/` (tightly-coupled baseline vs. provider-abstracted
  version).
- Positive: benchmarking is uniform — `app/benchmarks/engine.py` calls the
  same three methods regardless of algorithm family.
- Negative: the interface is deliberately primitive-level, not
  protocol-level (no real TLS handshake is terminated) — this is an
  explicit scope limitation (Section 60), not an oversight.
- Negative: hybrid support is KEM-only; a hybrid *signature* provider would
  need a separate composition strategy not yet implemented.

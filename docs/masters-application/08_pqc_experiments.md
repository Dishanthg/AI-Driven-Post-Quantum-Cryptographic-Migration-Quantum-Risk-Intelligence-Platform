# 08. PQC Experiments

REAL BENCHMARK DATA, executed on the development machine (`make benchmark`,
30 iterations/algorithm/operation, `research/tables/benchmark_sweep.csv`).
Not extrapolated, not looked up from vendor spec sheets.

## Key generation time (mean, ms)
| Algorithm | Family | Keygen mean (ms) |
|---|---|---|
| ML-KEM-512 | PQC KEM | 0.098 |
| ECDH-P256 | Classical | 0.173 |
| ECDSA-P256 | Classical | 0.185 |
| ML-KEM-768 | PQC KEM | 0.218 |
| ML-KEM-1024 | PQC KEM | 0.237 |
| HYBRID-ECDH-ML-KEM-768 | Hybrid | 0.368 |
| ML-DSA-44 | PQC signature | 0.469 |
| ML-DSA-65 | PQC signature | 0.613 |
| DH-2048 | Classical | 1.922 |
| ML-DSA-87 | PQC signature | 0.992 |
| SLH-DSA-SHA2-128F | PQC signature | 2.027 |
| RSA-2048 | Classical | 200.14 |
| RSA-3072 | Classical | 754.73 |

**Finding:** every ML-KEM/ML-DSA variant tested generates keys faster than
RSA at any tested modulus size — RSA-2048 keygen alone is ~2,000x slower
than ML-KEM-512. This directly complicates any assumption that "PQC is
slower" — for key generation specifically, the opposite is true here.

## Artifact sizes (bytes)
| Algorithm | Public key | Ciphertext/Signature |
|---|---|---|
| ECDSA-P256 | 91 | 70 (signature) |
| RSA-2048 | 294 | 256 (signature) |
| RSA-3072 | 422 | 384 (signature) |
| ML-KEM-512 | 800 | 768 (ciphertext) |
| ML-KEM-768 | 1184 | 1088 (ciphertext) |
| ML-DSA-44 | 1312 | 2420 (signature) |
| ML-KEM-1024 | 1568 | 1568 (ciphertext) |
| ML-DSA-65 | 1952 | 3309 (signature) |
| HYBRID-ECDH-ML-KEM-768 | 1279 | 1183 (ciphertext) |
| ML-DSA-87 | 2592 | 4627 (signature) |
| SLH-DSA-SHA2-128F | 32 | **17,088** (signature) |

**Finding:** PQC's real cost shows up here, not in speed. ML-DSA-65's
signature is ~47x larger than ECDSA-P256's; SLH-DSA-SHA2-128F's is ~244x
larger — a genuine bandwidth/storage concern for high-signature-volume or
constrained-bandwidth use cases (e.g. IoT, high-frequency API signing),
even though its *public key* is unusually small (32 bytes, smaller than
ECDSA's).

## Sign/verify cost
Signing is consistently more expensive than verification across every
signature algorithm tested, and PQC signing costs (ML-DSA-65 ≈27.3ms,
SLH-DSA-SHA2-128F ≈39.4ms) are meaningfully higher than ECDSA-P256's
≈0.18ms — a real trade-off, not assumed.

## Hybrid overhead (Experiment 5, partial — KEM only)
HYBRID-ECDH-ML-KEM-768 encapsulate (≈1.01ms) costs more than ML-KEM-768
alone (≈0.25ms) — expected, since it performs both the classical ECDH and
the PQC KEM operation and combines the results via HKDF. No hybrid
signature composition was implemented (explicit scope limitation).

## Honest overall takeaway
"Is PQC slower/bigger than classical crypto" does not have a single answer
— it depends on which operation and which classical baseline you compare
against. Keygen: PQC often faster. Artifact size: PQC (especially
signatures) is consistently and sometimes dramatically larger. This
granularity is the point of measuring rather than assuming (Section 18:
"Do not assume PQC is slower or faster. Measure it.").

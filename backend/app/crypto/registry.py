"""AlgorithmRegistry: the single source of truth for algorithm classification.

Every other module (discovery, threat model, benchmarking, recommendation engine,
API) must look algorithms up here rather than re-implementing classification
logic inline (design doc Section I / Section 9: "Do not hard-code the
classification throughout the application").

Sizes for PQC entries are the exact values returned by the underlying PQClean
implementations at runtime (see backend/tests/test_crypto_providers.py, which
asserts the values below match what the library actually reports) - not
hand-copied from the spec. Classical sizes are standard, well-known values.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- classification taxonomy (Section 9) -----------------------------------
CLASSICAL_PK = "classical_pk"
CLASSICAL_SYM = "classical_sym"
HASH = "hash"
PQC_KEM = "pqc_kem"
PQC_SIG = "pqc_sig"
HYBRID = "hybrid"

# --- quantum vulnerability classes (Section J of design doc) ---------------
QUANTUM_VULNERABLE = "quantum_vulnerable"       # broken in poly-time by Shor under the standard circuit model
QUANTUM_WEAKENED = "quantum_weakened"            # security margin roughly halved by Grover's quadratic speedup
NOT_SIGNIFICANTLY_AFFECTED = "not_significantly_affected"  # standardized PQC target


@dataclass(frozen=True)
class AlgorithmSpec:
    id: str
    name: str
    family: str
    role: str  # public_key | key_exchange | signature | symmetric | hash
    classification: str
    security_basis: str
    quantum_vulnerability: str
    standard_ref: str = ""
    library_source: str = ""
    typical_key_size_bits: int = 0
    provider_key: str | None = None  # key into crypto/providers.py operation tables, if operable
    notes: str = field(default="")


REGISTRY: dict[str, AlgorithmSpec] = {}


def _register(spec: AlgorithmSpec) -> AlgorithmSpec:
    REGISTRY[spec.id] = spec
    return spec


# ---------------------------------------------------------------- classical -
_register(AlgorithmSpec(
    id="RSA-2048", name="RSA-2048", family="RSA", role="public_key",
    classification=CLASSICAL_PK, security_basis="integer_factorization",
    quantum_vulnerability=QUANTUM_VULNERABLE,
    standard_ref="FIPS 186-5", library_source="cryptography (pyca)",
    typical_key_size_bits=2048, provider_key="rsa2048",
    notes="Broken in polynomial time by Shor's algorithm on a sufficiently large fault-tolerant quantum computer.",
))
_register(AlgorithmSpec(
    id="RSA-3072", name="RSA-3072", family="RSA", role="public_key",
    classification=CLASSICAL_PK, security_basis="integer_factorization",
    quantum_vulnerability=QUANTUM_VULNERABLE,
    standard_ref="FIPS 186-5", library_source="cryptography (pyca)",
    typical_key_size_bits=3072, provider_key="rsa3072",
))
_register(AlgorithmSpec(
    id="ECDSA-P256", name="ECDSA P-256", family="ECC", role="signature",
    classification=CLASSICAL_PK, security_basis="elliptic_curve_discrete_log",
    quantum_vulnerability=QUANTUM_VULNERABLE,
    standard_ref="FIPS 186-5", library_source="cryptography (pyca)",
    typical_key_size_bits=256, provider_key="ecdsa_p256",
))
_register(AlgorithmSpec(
    id="ECDH-P256", name="ECDH P-256", family="ECC", role="key_exchange",
    classification=CLASSICAL_PK, security_basis="elliptic_curve_discrete_log",
    quantum_vulnerability=QUANTUM_VULNERABLE,
    standard_ref="SP 800-56A", library_source="cryptography (pyca)",
    typical_key_size_bits=256, provider_key="ecdh_p256",
))
_register(AlgorithmSpec(
    id="DH-2048", name="Diffie-Hellman (2048-bit MODP)", family="DH", role="key_exchange",
    classification=CLASSICAL_PK, security_basis="discrete_log",
    quantum_vulnerability=QUANTUM_VULNERABLE,
    standard_ref="RFC 3526", library_source="cryptography (pyca)",
    typical_key_size_bits=2048, provider_key="dh2048",
))
_register(AlgorithmSpec(
    id="AES-128-GCM", name="AES-128-GCM", family="AES", role="symmetric",
    classification=CLASSICAL_SYM, security_basis="block_cipher",
    quantum_vulnerability=QUANTUM_WEAKENED,
    standard_ref="FIPS 197 / SP 800-38D", library_source="cryptography (pyca)",
    typical_key_size_bits=128,
    notes="Grover's algorithm gives a quadratic speedup for exhaustive key search; effective security margin reduces to roughly 64 bits.",
))
_register(AlgorithmSpec(
    id="AES-256-GCM", name="AES-256-GCM", family="AES", role="symmetric",
    classification=CLASSICAL_SYM, security_basis="block_cipher",
    quantum_vulnerability=QUANTUM_WEAKENED,
    standard_ref="FIPS 197 / SP 800-38D", library_source="cryptography (pyca)",
    typical_key_size_bits=256,
    notes="Grover reduces effective margin to roughly 128 bits, still considered adequate.",
))
_register(AlgorithmSpec(
    id="SHA-256", name="SHA-256", family="SHA2", role="hash",
    classification=HASH, security_basis="hash_preimage_collision",
    quantum_vulnerability=QUANTUM_WEAKENED,
    standard_ref="FIPS 180-4", library_source="cryptography (pyca)", typical_key_size_bits=256,
))
_register(AlgorithmSpec(
    id="SHA-384", name="SHA-384", family="SHA2", role="hash",
    classification=HASH, security_basis="hash_preimage_collision",
    quantum_vulnerability=QUANTUM_WEAKENED,
    standard_ref="FIPS 180-4", library_source="cryptography (pyca)", typical_key_size_bits=384,
))
_register(AlgorithmSpec(
    id="SHA-512", name="SHA-512", family="SHA2", role="hash",
    classification=HASH, security_basis="hash_preimage_collision",
    quantum_vulnerability=QUANTUM_WEAKENED,
    standard_ref="FIPS 180-4", library_source="cryptography (pyca)", typical_key_size_bits=512,
))

# --------------------------------------------------------------------- pqc --
_register(AlgorithmSpec(
    id="ML-KEM-512", name="ML-KEM-512", family="ML-KEM", role="key_exchange",
    classification=PQC_KEM, security_basis="module_lattice_lwe",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 203", library_source="pqcrypto (PQClean)", typical_key_size_bits=800 * 8,
    provider_key="ml_kem_512",
))
_register(AlgorithmSpec(
    id="ML-KEM-768", name="ML-KEM-768", family="ML-KEM", role="key_exchange",
    classification=PQC_KEM, security_basis="module_lattice_lwe",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 203", library_source="pqcrypto (PQClean)", typical_key_size_bits=1184 * 8,
    provider_key="ml_kem_768",
))
_register(AlgorithmSpec(
    id="ML-KEM-1024", name="ML-KEM-1024", family="ML-KEM", role="key_exchange",
    classification=PQC_KEM, security_basis="module_lattice_lwe",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 203", library_source="pqcrypto (PQClean)", typical_key_size_bits=1568 * 8,
    provider_key="ml_kem_1024",
))
_register(AlgorithmSpec(
    id="ML-DSA-44", name="ML-DSA-44", family="ML-DSA", role="signature",
    classification=PQC_SIG, security_basis="module_lattice_fiat_shamir",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 204", library_source="pqcrypto (PQClean)", typical_key_size_bits=1312 * 8,
    provider_key="ml_dsa_44",
))
_register(AlgorithmSpec(
    id="ML-DSA-65", name="ML-DSA-65", family="ML-DSA", role="signature",
    classification=PQC_SIG, security_basis="module_lattice_fiat_shamir",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 204", library_source="pqcrypto (PQClean)", typical_key_size_bits=1952 * 8,
    provider_key="ml_dsa_65",
))
_register(AlgorithmSpec(
    id="ML-DSA-87", name="ML-DSA-87", family="ML-DSA", role="signature",
    classification=PQC_SIG, security_basis="module_lattice_fiat_shamir",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 204", library_source="pqcrypto (PQClean)", typical_key_size_bits=2592 * 8,
    provider_key="ml_dsa_87",
))
_register(AlgorithmSpec(
    id="SLH-DSA-SHA2-128F", name="SLH-DSA-SHA2-128f", family="SLH-DSA", role="signature",
    classification=PQC_SIG, security_basis="hash_based_merkle",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="FIPS 205", library_source="pqcrypto (PQClean)", typical_key_size_bits=32 * 8,
    provider_key="slh_dsa_sha2_128f",
    notes="Hash-based signature; larger/slower than lattice schemes but relies only on hash-function security assumptions.",
))
_register(AlgorithmSpec(
    id="HYBRID-ECDH-ML-KEM-768", name="Hybrid ECDH-P256 + ML-KEM-768", family="HYBRID", role="key_exchange",
    classification=HYBRID, security_basis="ecdlp+module_lattice_lwe",
    quantum_vulnerability=NOT_SIGNIFICANTLY_AFFECTED,
    standard_ref="draft-ietf-tls-hybrid-design", library_source="composition of pyca + pqcrypto",
    provider_key="hybrid_ecdh_mlkem768",
    notes="Transitional composition: shared secret derived from both classical ECDH and ML-KEM-768; "
          "secure if either component remains secure, at the cost of both computational overheads.",
))


def get(algorithm_id: str) -> AlgorithmSpec:
    if algorithm_id not in REGISTRY:
        raise KeyError(f"Unknown algorithm id: {algorithm_id!r}")
    return REGISTRY[algorithm_id]


def list_by_classification(classification: str) -> list[AlgorithmSpec]:
    return [a for a in REGISTRY.values() if a.classification == classification]


def get_by_provider_key(provider_key: str) -> AlgorithmSpec:
    for spec in REGISTRY.values():
        if spec.provider_key == provider_key:
            return spec
    raise KeyError(f"No registered algorithm for provider_key: {provider_key!r}")


def all_specs() -> list[AlgorithmSpec]:
    return list(REGISTRY.values())

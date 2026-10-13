"""Static, citation-backed quantum threat reference engine (design doc Section J
/ Section 10). This module is deliberately NOT a "live risk calculator" - it is
a lookup table of textbook cryptanalytic facts, used as a feature source for
the AI risk engine and displayed verbatim in the UI. It never claims a
real-world key has been or can be broken by this project (Rules 2-5).

Sources: Shor, P. "Polynomial-Time Algorithms for Prime Factorization and
Discrete Logarithms on a Quantum Computer" (SIAM J. Comput., 1997); Grover, L.
"A fast quantum mechanical algorithm for database search" (STOC 1996); NIST
IR 8413 (status report on the 3rd PQC standardization round); NIST SP 800-131A
transition guidance.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.crypto import registry as algo_registry


@dataclass(frozen=True)
class ThreatEntry:
    algorithm_family: str
    attack_model: str  # "Shor's algorithm" | "Grover's algorithm" | "none known"
    classical_security_assumption: str
    theoretical_quantum_complexity: str
    practical_constraint: str
    current_limitation: str
    plain_language_explanation: str


THREAT_TABLE: dict[str, ThreatEntry] = {
    "RSA": ThreatEntry(
        algorithm_family="RSA",
        attack_model="Shor's algorithm",
        classical_security_assumption="Hardness of integer factorization",
        theoretical_quantum_complexity="Polynomial time, O((log N)^2 log log N) gate-model circuit "
                                        "for an n-bit modulus (Shor, 1997)",
        practical_constraint="Requires on the order of 2n-3n logical, fully error-corrected qubits for an "
                              "n-bit modulus (widely varies by compilation), i.e. several thousand logical "
                              "qubits for RSA-2048 - which in turn require millions of physical qubits under "
                              "current error-correction overhead estimates. No such machine exists as of 2026.",
        current_limitation="Largest experimentally demonstrated Shor-style factorizations on real quantum "
                            "hardware remain limited to small numbers (comparable in scale to this project's "
                            "own N=15/21 lab, not to RSA-scale moduli).",
        plain_language_explanation="Shor's algorithm provides a polynomial-time quantum approach to integer "
                                    "factoring under the standard circuit model, motivating a transition toward "
                                    "post-quantum cryptographic schemes; it does not mean RSA is broken today.",
    ),
    "ECC": ThreatEntry(
        algorithm_family="ECC (ECDSA/ECDH)",
        attack_model="Shor's algorithm (discrete-log variant)",
        classical_security_assumption="Hardness of the elliptic-curve discrete logarithm problem (ECDLP)",
        theoretical_quantum_complexity="Polynomial time via a quantum discrete-log algorithm (Shor, 1997; "
                                        "Proos & Zalka circuit estimates for elliptic curves)",
        practical_constraint="ECC's smaller classical key sizes require fewer logical qubits than RSA for an "
                              "equivalent classical security level, but still well beyond current fault-tolerant "
                              "hardware (thousands of logical qubits for P-256).",
        current_limitation="No large-scale fault-tolerant quantum computer exists to run this circuit at "
                            "cryptographically relevant curve sizes.",
        plain_language_explanation="The same theoretical quantum advantage that threatens RSA applies to "
                                    "ECDSA/ECDH via a discrete-log variant of Shor's algorithm; ECC is not "
                                    "additionally 'safe' by virtue of using smaller keys.",
    ),
    "DH": ThreatEntry(
        algorithm_family="Diffie-Hellman (finite field)",
        attack_model="Shor's algorithm (discrete-log variant)",
        classical_security_assumption="Hardness of the discrete logarithm problem in a finite field",
        theoretical_quantum_complexity="Polynomial time (Shor, 1997)",
        practical_constraint="Comparable logical-qubit requirements to RSA at equivalent classical security levels.",
        current_limitation="No large-scale fault-tolerant hardware exists.",
        plain_language_explanation="Finite-field Diffie-Hellman shares RSA's vulnerability profile under Shor's "
                                    "algorithm.",
    ),
    "AES": ThreatEntry(
        algorithm_family="AES (symmetric)",
        attack_model="Grover's algorithm",
        classical_security_assumption="No known structural weakness; security from key-space exhaustive search "
                                        "being computationally infeasible classically",
        theoretical_quantum_complexity="Quadratic speedup for exhaustive key search: O(2^(k/2)) quantum queries "
                                        "vs O(2^k) classical, for a k-bit key (Grover, 1996)",
        practical_constraint="Requires a large number of sequential (non-parallelizable) coherent quantum "
                              "operations, and implementing an AES oracle as a quantum circuit itself has "
                              "substantial resource cost (Grassl et al. give circuit estimates in the "
                              "thousands of logical qubits for full Grover key search on AES).",
        current_limitation="Even granting a future fault-tolerant machine, Grover's algorithm only "
                            "quadratically - not exponentially - reduces AES's security margin.",
        plain_language_explanation="Grover's algorithm provides a theoretical quadratic (not exponential) "
                                    "speedup for brute-forcing symmetric keys; doubling the key length "
                                    "(e.g. AES-256 instead of AES-128) restores the original security margin.",
    ),
    "HASH": ThreatEntry(
        algorithm_family="Cryptographic hash functions (SHA-2 family)",
        attack_model="Grover's algorithm (preimage search)",
        classical_security_assumption="Preimage/collision resistance from the difficulty of inverting/colliding "
                                        "the compression function",
        theoretical_quantum_complexity="Quadratic speedup for preimage search: O(2^(n/2)) vs O(2^n) for an "
                                        "n-bit hash",
        practical_constraint="Same coherent-circuit-depth constraints as the AES case.",
        current_limitation="No practical demonstration beyond small toy circuits exists.",
        plain_language_explanation="As with AES, Grover's algorithm only quadratically weakens hash-based "
                                    "preimage resistance; SHA-384/SHA-512 retain a large security margin under "
                                    "this model.",
    ),
    "PQC": ThreatEntry(
        algorithm_family="Standardized post-quantum algorithms (ML-KEM/ML-DSA/SLH-DSA)",
        attack_model="No known efficient quantum algorithm",
        classical_security_assumption="Hardness of structured lattice problems (Module-LWE/Module-SIS) or, for "
                                        "SLH-DSA, only the security of an underlying hash function",
        theoretical_quantum_complexity="No known polynomial-time quantum algorithm as of NIST's 2024 "
                                        "standardization (FIPS 203/204/205); best known quantum attacks are "
                                        "based on quantum-accelerated lattice reduction, which remains "
                                        "exponential in the relevant security parameters.",
        practical_constraint="N/A - these are the algorithms organizations are migrating toward.",
        current_limitation="Cryptanalysis of lattice problems under quantum models is an active research area; "
                            "these algorithms are 'designed to provide resistance against known quantum attack "
                            "models,' not proven unconditionally secure (Rule 7).",
        plain_language_explanation="ML-KEM/ML-DSA/SLH-DSA are standardized to resist all currently known "
                                    "classical and quantum cryptanalytic techniques, based on problems believed "
                                    "hard for both classical and quantum computers.",
    ),
}

_FAMILY_MAP = {
    "RSA": "RSA", "ECC": "ECC", "DH": "DH", "AES": "AES", "SHA2": "HASH",
    "ML-KEM": "PQC", "ML-DSA": "PQC", "SLH-DSA": "PQC", "HYBRID": "PQC",
}


def threat_for_algorithm(algorithm_id: str) -> ThreatEntry:
    spec = algo_registry.get(algorithm_id)
    key = _FAMILY_MAP.get(spec.family, "PQC")
    return THREAT_TABLE[key]

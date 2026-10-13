# 02. Quantum Motivation

## Why quantum computing matters to this project's cryptography choices
Two quantum algorithms motivate the entire migration problem QuantumShield
models:

**Shor's algorithm** (Shor, 1997) gives a polynomial-time quantum approach
to integer factorization and the discrete logarithm problem, under the
standard gate-model circuit assumption. That directly threatens RSA
(factoring), and — via a discrete-log variant — ECDSA/ECDH and finite-field
Diffie-Hellman. `backend/app/quantum/threat_model.py` records this per
algorithm family with the theoretical complexity, a practical qubit-count
constraint (RSA-2048 needs on the order of thousands of logical,
fully-error-corrected qubits, which in turn need millions of physical
qubits under current error-correction overhead estimates), and the current
experimental limitation (real hardware has only factored numbers on the
scale of this project's own N=15/21 Shor lab — not RSA-scale moduli).

**Grover's algorithm** (Grover, 1996) gives a quadratic speedup for
unstructured search, which translates to halving the effective key-space
exponent for symmetric-key exhaustive search (e.g. AES-128 drops from a
2^128 classical security margin to roughly 2^64 quantum queries under
Grover) — a security-margin reduction, not a break, and the standard
mitigation (moving to AES-256) is well understood and already reflected in
NIST guidance.

## Why this project treats that motivation carefully
The gap between "polynomial-time quantum algorithm exists in theory" and
"a real quantum computer can execute it against a 2048-bit modulus" is
enormous and is the single most commonly overstated fact in popular
discussion of "quantum threatens encryption." This project's Rule 2-5
(see the build specification) forbid claiming real-world RSA/ECC has been
broken, and require every quantum result the platform produces to be
labeled with its actual scale and simulator/hardware status. The Shor and
Grover labs (`backend/app/quantum/shor_lab.py`,
`backend/app/quantum/grover_lab.py`) are hard-capped at 16 qubits
(`docs/architecture/adr/ADR-006-quantum-simulation-scope.md`) specifically
so the platform cannot be pointed at anything that could be misread as a
real attack, even by accident or misconfiguration.

## What the project actually demonstrates about quantum computing
Not "we broke encryption" — rather: (1) a working, tested implementation of
Shor's period-finding approach via quantum phase estimation, correctly
factoring 15=3×5 and 21=7×3 on a real Qiskit Aer simulator; (2) a working
Grover search achieving ~96.5% measured success probability at its
theoretically optimal iteration count; (3) a real demonstration that even
modest per-gate noise (0.1%/1% depolarizing, 2% readout error) collapses
Grover's success probability from 96% to 44% (Experiment 8) — a concrete,
measured illustration of why today's NISQ-era hardware is far from posing
the threat the *theoretical* algorithms describe. That gap — theoretical
capability vs. noisy-hardware reality vs. the still-more-distant
fault-tolerant regime Shor's algorithm actually needs at cryptographic
scale — is itself the motivation for post-quantum cryptography: migrate
*before* the gap closes, not after, because cryptographic transitions take
years and "harvest now, decrypt later" attacks on long-lived encrypted data
are a present-day risk even though large-scale quantum decryption is not.

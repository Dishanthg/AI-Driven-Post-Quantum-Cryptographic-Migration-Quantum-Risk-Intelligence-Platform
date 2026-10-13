# ADR-006: Quantum labs are scale-capped simulators, structurally incapable of touching cryptographic key sizes

## Status
Accepted, implemented (`backend/app/quantum/grover_lab.py`,
`backend/app/quantum/shor_lab.py`, `Settings.quantum_max_qubits`).

## Context
This is the highest-stakes integrity decision in the project. Rules 2-5 and
Section 63 ("Quantum Research Integrity") are unambiguous: the project must
never claim, imply, or leave room to be misread as claiming that it can break
real RSA/ECC/AES. Grover and Shor labs are required by Section 7/11/12/13 for
genuine pedagogical and research value (H6/RQ7) — but a demo that "looks
real" while quietly capping qubits only in a config default is one parameter
change away from someone pointing it at something that reads as
cryptographically meaningful.

## Problem
How do we make the "this cannot touch real key sizes" property a structural
guarantee rather than a promise in a docstring?

## Alternatives considered
- **Document the limitation, trust callers not to raise the qubit count.**
  Rejected — a comment is not a control; Rule 15 requires the system itself
  to be honest, not just its documentation.
- **Cap only in the API layer.** Rejected as insufficient on its own — the
  lab modules are also runnable directly (`make quantum-lab`,
  `python -m app.quantum.shor_lab`) and must be safe there too, not only
  behind the FastAPI request path.
- **No cap; rely on classical simulators' exponential resource wall to make
  large instances practically infeasible anyway.** Rejected — "impractical"
  is not the same guarantee as "structurally refused," and a sufficiently
  patient/well-resourced user could still run something large enough to
  invite exactly the misreading Rule 2/3 forbids.

## Decision
`Settings.quantum_max_qubits = 16` is enforced at **every** entry point:
- `grover_lab.py` raises `ValueError` if `n_qubits` exceeds the cap, inside
  the lab function itself — not just at the API boundary — so the lab is
  "structurally incapable of being pointed at a cryptographically relevant
  key space (e.g. AES-128's 2^128)" (module docstring, verbatim).
- `shor_lab.py` similarly hard-caps `counting_qubits` and only exposes small
  composite numbers (15, 21, and similar) as factoring targets — nowhere
  near RSA-scale.
- The FastAPI routes (`api/routers/quantum.py`) additionally return HTTP 422
  before even calling the lab, citing this ADR, so the failure is visible at
  the API contract level too (defense in depth, not redundant duplication).
- Every quantum lab result is labeled QUANTUM SIMULATION (Aer
  statevector/qasm simulator) — never conflated with real quantum hardware
  (Section 48, Rule 14) — enforced by
  `tests/test_research_integrity.py::test_quantum_lab_results_are_always_labeled`
  and `tests/test_quantum_labs.py::test_shor_caveat_never_claims_rsa_broken`.

## Consequences
- Positive: the "cannot break real cryptography" property is enforced by
  code that fails loudly (raises) rather than documentation that could be
  ignored, and is covered by a dedicated regression test.
- Positive: this directly operationalizes RQ7/H6 — the labs remain
  "computationally infeasible for realistic cryptographic key sizes on
  classical simulators," but here that's a design guarantee, not just an
  observation about Aer's runtime.
- Negative / accepted trade-off: the cap means the lab cannot demonstrate
  Shor's algorithm against anything resembling a real key size, even for
  illustration — this is the entire point, not a limitation to work around.

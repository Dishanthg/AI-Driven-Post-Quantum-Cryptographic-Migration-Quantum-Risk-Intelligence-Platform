# 07. Quantum Experiments

All results below are QUANTUM SIMULATION (Qiskit Aer), never real quantum
hardware — this repository has no hardware backend integration. All are
VERIFIED via automated tests (`backend/tests/test_quantum_labs.py`,
`test_research_integrity.py`) and/or direct re-execution during this
session.

## Grover lab (Experiment 7)
- 4-qubit register (16-item search space), 1 marked state, 2048-4096 shots.
- Theoretically optimal iteration count computed as
  `round((π/4)·√(N/M))` = 3 for this configuration.
- Measured success probability: **~96.1-96.5%** (varies slightly by shot
  count/seed across runs) — consistent with the theoretical bound for this
  small an instance, not a fabricated round number.
- Circuit depth after transpilation: 14 (ideal basis gate set).
- Hard-capped at `quantum_max_qubits=16` (65,536-item max search space) —
  enforced by a `ValueError` inside the lab function itself, not only at
  the API layer (`ADR-006`).

## Shor lab (Experiment 7)
- Quantum phase estimation over modular exponentiation, classical
  continued-fractions period extraction.
- Correctly factored **15 = 3×5** and **21 = 7×3** on the Aer simulator.
- `tests/test_quantum_labs.py::test_shor_caveat_never_claims_rsa_broken`
  asserts the result object's caveat text does not imply real-world
  RSA/factoring capability — this is enforced by an automated test, not
  just a docstring promise.

## Noise analysis (Experiment 8)
- Same 4-qubit Grover configuration, ideal `AerSimulator` vs. a
  depolarizing (0.1% single-qubit gates, 1% CX) + readout-error (2%) noise
  model — explicitly labeled as illustrative NISQ-like rates, not fitted to
  a specific real device.
- **Ideal:** success probability 0.9614, circuit depth 14.
- **Noisy:** success probability 0.4387, circuit depth 171 (post-
  transpilation to a noise-eligible basis gate set).
- **Real quantum hardware: NOT RUN** (Section 39's explicit fallback —
  no IBM Quantum or other hardware credentials/integration exist in this
  codebase).
- Interpretation: a ~55-percentage-point success-probability collapse from
  modest per-gate error rates illustrates concretely why current NISQ-era
  hardware is far short of what Shor's algorithm would need to run
  reliably at cryptographically relevant scale, where the required circuit
  depth is orders of magnitude larger than this lab's.

## Complexity framing shown alongside every result
Every quantum-lab result the platform surfaces (API, frontend) is paired
with: the classical baseline complexity for the same problem, the
theoretical quantum complexity, and an explicit statement that the lab's
scale is many orders of magnitude below any cryptographically relevant
instance (Section 13's "separate asymptotic complexity from practical
execution time" requirement).

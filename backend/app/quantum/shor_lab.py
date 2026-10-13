"""Small-scale Shor factoring laboratory (design doc Section 11 / Experiment 7).

Implements genuine quantum order-finding via Quantum Phase Estimation (QPE):
  1. classical pre-check (gcd shortcut, as in the real algorithm)
  2. build the modular-multiplication unitary U_a: |y> -> |a*y mod N> as an
     explicit permutation matrix on ceil(log2(N)) qubits (padded with identity
     on unused basis states to remain unitary) - this is a standard small-N
     simulation technique, not a shortcut that fakes the answer: the QPE
     circuit is built and executed for real, and the measured phase is what
     yields the period.
  3. QPE with controlled-U_a^(2^j) (computed via explicit matrix power, since
     U_a is a permutation) to estimate the order r of a mod N
  4. classical continued-fractions post-processing to recover r, then
     gcd(a^(r/2) +/- 1, N) to recover a nontrivial factor.

HARD SCOPE LIMIT: N is capped so total qubits (target + counting) never exceed
`settings.quantum_max_qubits`. This makes it structurally impossible to point
this lab at an RSA-scale modulus (Rule 2/3/4/5).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFT, UnitaryGate
from qiskit_aer import AerSimulator

from app.core.config import get_settings


@dataclass
class ShorResult:
    N: int
    a: int
    target_qubits: int
    counting_qubits: int
    total_qubits: int
    circuit_depth: int
    shots: int
    measured_phase_bitstrings: dict[str, int]
    period_found: int | None
    factors: tuple[int, int] | None
    success: bool
    runtime_seconds: float
    classical_shortcut_used: bool
    backend: str = "aer_simulator"
    data_label: str = "QUANTUM SIMULATION"
    hardware_type: str = "SIMULATOR"
    caveat: str = field(default=(
        "Small-scale simulation (N <= a few tens) for educational/research purposes only. "
        "This does NOT demonstrate breaking RSA or any real-world key: factoring RSA-2048 "
        "would require thousands of logical, fully error-corrected qubits, which do not "
        "exist. Runtime/qubit growth here is intentionally shown to scale poorly on a "
        "classical simulator as N grows (see Experiment 7 results)."
    ))


def _mod_mult_unitary(a: int, N: int, n_target: int) -> np.ndarray:
    dim = 2 ** n_target
    U = np.zeros((dim, dim))
    for x in range(dim):
        y = (a * x) % N if x < N else x
        U[y, x] = 1.0
    # any remaining unmapped diagonal (shouldn't occur since mapping is a bijection on [0,N) and identity elsewhere)
    return U


def _controlled_power_gate(a: int, N: int, n_target: int, power: int) -> UnitaryGate:
    U = _mod_mult_unitary(a, N, n_target)
    Upow = np.linalg.matrix_power(U, power)
    gate = UnitaryGate(Upow, label=f"U_{a}^{power} mod {N}")
    return gate.control(1)


def _order_via_continued_fractions(phase: float, N: int) -> int | None:
    frac = Fraction(phase).limit_denominator(N)
    r = frac.denominator
    return r if 0 < r < N else None


def factor_via_shor(N: int, a: int | None = None, counting_qubits: int = 8, shots: int = 2048, seed: int = 42) -> ShorResult:
    settings = get_settings()
    if N < 4:
        raise ValueError("N must be >= 4")
    if N % 2 == 0:
        return ShorResult(
            N=N, a=0, target_qubits=0, counting_qubits=0, total_qubits=0, circuit_depth=0,
            shots=shots, measured_phase_bitstrings={}, period_found=None, factors=(2, N // 2),
            success=True, runtime_seconds=0.0, classical_shortcut_used=True,
        )

    n_target = max(1, math.ceil(math.log2(N)))
    total_qubits = n_target + counting_qubits
    if total_qubits > settings.quantum_max_qubits:
        raise ValueError(
            f"N={N} with {counting_qubits} counting qubits needs {total_qubits} total qubits, "
            f"exceeding lab cap of {settings.quantum_max_qubits}. Reduce N or counting_qubits."
        )

    rng = np.random.default_rng(seed)
    if a is None:
        candidates = [x for x in range(2, N) if math.gcd(x, N) == 1]
        a = int(rng.choice(candidates))

    g = math.gcd(a, N)
    if g > 1:
        return ShorResult(
            N=N, a=a, target_qubits=n_target, counting_qubits=counting_qubits,
            total_qubits=n_target + counting_qubits, circuit_depth=0, shots=shots,
            measured_phase_bitstrings={}, period_found=None, factors=(g, N // g),
            success=True, runtime_seconds=0.0, classical_shortcut_used=True,
        )

    qc = QuantumCircuit(counting_qubits + n_target, counting_qubits)
    counting = list(range(counting_qubits))
    target = list(range(counting_qubits, counting_qubits + n_target))

    qc.h(counting)
    qc.x(target[0])  # initialize target register to |1>

    for j in range(counting_qubits):
        power = 2 ** j
        cgate = _controlled_power_gate(a, N, n_target, power)
        qc.append(cgate, [counting[j], *target])

    qc.append(QFT(counting_qubits, inverse=True, do_swaps=True).to_gate(), counting)
    qc.measure(counting, list(range(counting_qubits)))

    backend = AerSimulator(seed_simulator=seed)
    t0 = time.perf_counter()
    tqc = transpile(qc, backend)
    job = backend.run(tqc, shots=shots, seed_simulator=seed)
    result = job.result()
    runtime = time.perf_counter() - t0
    counts = result.get_counts()

    best_period = None
    for bitstring, _freq in sorted(counts.items(), key=lambda kv: -kv[1]):
        phase = int(bitstring, 2) / (2 ** counting_qubits)
        if phase == 0:
            continue
        r = _order_via_continued_fractions(phase, N)
        if r and pow(a, r, N) == 1:
            best_period = r
            break

    factors = None
    success = False
    if best_period and best_period % 2 == 0:
        x = pow(a, best_period // 2, N)
        f1 = math.gcd(x - 1, N)
        f2 = math.gcd(x + 1, N)
        if f1 not in (1, N) and N % f1 == 0:
            factors = (f1, N // f1)
            success = True
        elif f2 not in (1, N) and N % f2 == 0:
            factors = (f2, N // f2)
            success = True

    return ShorResult(
        N=N, a=a, target_qubits=n_target, counting_qubits=counting_qubits,
        total_qubits=counting_qubits + n_target, circuit_depth=tqc.depth(), shots=shots,
        measured_phase_bitstrings=counts, period_found=best_period, factors=factors,
        success=success, runtime_seconds=runtime, classical_shortcut_used=False,
    )


if __name__ == "__main__":
    for N in (15, 21):
        result = factor_via_shor(N, counting_qubits=8, shots=2048)
        print(f"[{result.data_label} / {result.hardware_type}] N={result.N}, a={result.a}, "
              f"total_qubits={result.total_qubits}, period_found={result.period_found}, "
              f"factors={result.factors}, success={result.success}, "
              f"classical_shortcut_used={result.classical_shortcut_used}, "
              f"runtime={result.runtime_seconds:.4f}s")
    print(result.caveat)

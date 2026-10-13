"""Small-scale Grover search laboratory (design doc Section 12 / Experiment 7).

HARD SCOPE LIMIT: the search register is capped at `settings.quantum_max_qubits`
qubits (default 16 => search space <= 65536 items). This is architecturally
enforced (raises ValueError below the cap check), not just documented, so the
lab is structurally incapable of being pointed at a cryptographically relevant
key space (e.g. AES-128's 2^128). See docs/architecture/adr/ADR-006.

Every result is labeled QUANTUM SIMULATION (Aer statevector/qasm simulator),
never conflated with real quantum hardware (Rule 5/14).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from app.core.config import get_settings


@dataclass
class GroverResult:
    n_qubits: int
    search_space_size: int
    marked_states: list[str]
    iterations_used: int
    iterations_theoretical_optimal: int
    shots: int
    circuit_depth: int
    counts: dict[str, int]
    success_probability: float
    classical_expected_queries: float
    quantum_expected_queries: float
    runtime_seconds: float
    noise_model_applied: bool = False
    backend: str = "aer_simulator"
    data_label: str = "QUANTUM SIMULATION"
    hardware_type: str = "SIMULATOR"
    caveat: str = field(default=(
        "Small-scale simulation for educational/research purposes. Does NOT imply "
        "practical brute-forcing of real symmetric keys (e.g. AES) is feasible; Grover's "
        "algorithm only provides a quadratic query-complexity speedup, and this lab's "
        "search space is many orders of magnitude smaller than any real key space."
    ))


def _diffuser(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n, name="diffuser")
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))
    return qc


def _oracle(n: int, marked: list[int]) -> QuantumCircuit:
    qc = QuantumCircuit(n, name="oracle")
    for m in marked:
        bits = format(m, f"0{n}b")
        zero_positions = [i for i, b in enumerate(reversed(bits)) if b == "0"]
        if zero_positions:
            qc.x(zero_positions)
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)
        if zero_positions:
            qc.x(zero_positions)
    return qc


def run_grover(n_qubits: int, marked_states: list[int], shots: int = 2048, seed: int = 42, noise_model=None) -> GroverResult:
    settings = get_settings()
    if n_qubits < 2 or n_qubits > settings.quantum_max_qubits:
        raise ValueError(
            f"n_qubits must be in [2, {settings.quantum_max_qubits}] (lab scope cap); got {n_qubits}"
        )
    N = 2 ** n_qubits
    for m in marked_states:
        if not (0 <= m < N):
            raise ValueError(f"marked state {m} out of range for {n_qubits}-qubit register")

    M = len(marked_states)
    optimal_iterations = max(1, round((math.pi / 4) * math.sqrt(N / M)))

    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(range(n_qubits))
    oracle = _oracle(n_qubits, marked_states)
    diffuser = _diffuser(n_qubits)
    for _ in range(optimal_iterations):
        qc.compose(oracle, inplace=True)
        qc.compose(diffuser, inplace=True)
    qc.measure(range(n_qubits), range(n_qubits))

    backend = AerSimulator(seed_simulator=seed, noise_model=noise_model)
    t0 = time.perf_counter()
    tqc = transpile(qc, backend)
    job = backend.run(tqc, shots=shots, seed_simulator=seed)
    result = job.result()
    runtime = time.perf_counter() - t0

    counts = result.get_counts()
    marked_bitstrings = {format(m, f"0{n_qubits}b") for m in marked_states}
    success_shots = sum(c for bs, c in counts.items() if bs in marked_bitstrings)
    success_probability = success_shots / shots

    return GroverResult(
        n_qubits=n_qubits,
        search_space_size=N,
        marked_states=[format(m, f"0{n_qubits}b") for m in marked_states],
        iterations_used=optimal_iterations,
        iterations_theoretical_optimal=optimal_iterations,
        shots=shots,
        circuit_depth=tqc.depth(),
        counts=counts,
        success_probability=success_probability,
        classical_expected_queries=N / M / 2,
        quantum_expected_queries=optimal_iterations,
        runtime_seconds=runtime,
        noise_model_applied=noise_model is not None,
    )


if __name__ == "__main__":
    result = run_grover(n_qubits=4, marked_states=[5], shots=2048)
    print(f"[{result.data_label} / {result.hardware_type}] search space={result.search_space_size}, "
          f"marked={result.marked_states}, iterations={result.iterations_used}, "
          f"success_probability={result.success_probability:.4f}, circuit_depth={result.circuit_depth}, "
          f"runtime={result.runtime_seconds:.4f}s")
    print(f"Classical expected queries: {result.classical_expected_queries:.1f}; "
          f"quantum expected queries: {result.quantum_expected_queries}")
    print(result.caveat)

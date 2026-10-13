"""Experiment 8: Noise Analysis (design doc Section 39).

Runs the Grover lab under an IDEAL Aer simulator and under a NOISY Aer
simulator (a depolarizing + readout-error noise model, parameters loosely
representative of a real superconducting NISQ device's gate/readout error
rates - not calibrated against any specific real backend, which is stated
explicitly rather than implied), and compares success probability and
circuit depth.

REAL QUANTUM HARDWARE was NOT used and NOT attempted - this repository has
no IBM Quantum / other hardware credential integration. Per Section 39's
explicit instruction ("if real hardware is unavailable, clearly report NOT
RUN"), that row is reported as NOT RUN rather than omitted or simulated.

Run: python -m research.experiments.exp8_noise_analysis   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.quantum.grover_lab import run_grover  # noqa: E402
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error  # noqa: E402

N_QUBITS = 4
MARKED_STATES = [5]
SHOTS = 4096
SEED = 42

# Illustrative NISQ-like error rates (order-of-magnitude realistic for current
# superconducting hardware, NOT fitted to any specific real device):
ONE_QUBIT_DEPOL_RATE = 0.001   # 0.1% per single-qubit gate
TWO_QUBIT_DEPOL_RATE = 0.01    # 1% per two-qubit gate
READOUT_ERROR_RATE = 0.02      # 2% bit-flip on measurement


def _build_noise_model(n_qubits: int) -> NoiseModel:
    nm = NoiseModel()
    err1 = depolarizing_error(ONE_QUBIT_DEPOL_RATE, 1)
    err2 = depolarizing_error(TWO_QUBIT_DEPOL_RATE, 2)
    nm.add_all_qubit_quantum_error(err1, ["h", "x", "sx", "rz"])
    nm.add_all_qubit_quantum_error(err2, ["cx"])
    ro_error = ReadoutError([[1 - READOUT_ERROR_RATE, READOUT_ERROR_RATE],
                              [READOUT_ERROR_RATE, 1 - READOUT_ERROR_RATE]])
    for q in range(n_qubits):
        nm.add_readout_error(ro_error, [q])
    return nm


def main() -> int:
    ideal = run_grover(N_QUBITS, MARKED_STATES, shots=SHOTS, seed=SEED, noise_model=None)
    noisy = run_grover(N_QUBITS, MARKED_STATES, shots=SHOTS, seed=SEED, noise_model=_build_noise_model(N_QUBITS))

    result = {
        "experiment_id": "exp8_noise_analysis",
        "research_question": "RQ7/H6 (design doc Section 39): how does an ideal vs. noisy quantum simulator "
                              "affect Grover search success probability and circuit characteristics?",
        "backend_ideal": "qiskit_aer.AerSimulator (no noise model)",
        "backend_noisy": "qiskit_aer.AerSimulator with a depolarizing (1q=%.3f, 2q=%.3f) + readout-error "
                          "(%.3f) noise model - illustrative NISQ-like rates, NOT fitted to a specific "
                          "real backend" % (ONE_QUBIT_DEPOL_RATE, TWO_QUBIT_DEPOL_RATE, READOUT_ERROR_RATE),
        "real_quantum_hardware": "NOT RUN - no hardware backend credentials/integration exist in this "
                                  "repository (design doc Section 39 explicit fallback)",
        "n_qubits": N_QUBITS,
        "marked_states": MARKED_STATES,
        "shots": SHOTS,
        "ideal": {
            "success_probability": ideal.success_probability,
            "circuit_depth": ideal.circuit_depth,
            "runtime_seconds": ideal.runtime_seconds,
        },
        "noisy": {
            "success_probability": noisy.success_probability,
            "circuit_depth": noisy.circuit_depth,
            "runtime_seconds": noisy.runtime_seconds,
        },
        "success_probability_delta": noisy.success_probability - ideal.success_probability,
    }

    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "exp8_noise_analysis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    md = [
        "# Experiment 8: Noise Analysis (Grover lab, ideal vs. noisy simulator)\n",
        f"n_qubits={N_QUBITS}, marked_states={MARKED_STATES}, shots={SHOTS}. "
        "REAL QUANTUM HARDWARE: NOT RUN (no hardware backend integration in this repo).\n",
        "| backend | success probability | circuit depth |",
        "|---|---|---|",
        f"| ideal (AerSimulator, no noise) | {ideal.success_probability:.4f} | {ideal.circuit_depth} |",
        f"| noisy (depolarizing + readout error) | {noisy.success_probability:.4f} | {noisy.circuit_depth} |",
        "| real quantum hardware | NOT RUN | NOT RUN |",
        f"\nSuccess probability delta (noisy - ideal): {result['success_probability_delta']:+.4f}\n",
    ]
    (out_dir / "exp8_noise_analysis.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

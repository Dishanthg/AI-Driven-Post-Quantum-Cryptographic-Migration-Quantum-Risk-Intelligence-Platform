"""Verifies the quantum labs' hard scope limits (Rule 2-5) and correctness of
the small-scale results they DO produce."""
from __future__ import annotations

import pytest

from app.quantum.grover_lab import run_grover
from app.quantum.shor_lab import factor_via_shor


def test_grover_finds_marked_state_with_high_probability():
    result = run_grover(n_qubits=4, marked_states=[5], shots=4096, seed=42)
    assert result.search_space_size == 16
    assert result.success_probability > 0.8  # Grover with optimal iterations should succeed most of the time
    assert result.data_label == "QUANTUM SIMULATION"
    assert result.hardware_type == "SIMULATOR"


def test_grover_rejects_qubit_count_above_lab_cap():
    from app.core.config import get_settings
    cap = get_settings().quantum_max_qubits
    with pytest.raises(ValueError):
        run_grover(n_qubits=cap + 1, marked_states=[0])


def test_grover_rejects_marked_state_out_of_range():
    with pytest.raises(ValueError):
        run_grover(n_qubits=3, marked_states=[100])


@pytest.mark.parametrize("N,expected_factors", [(15, {3, 5}), (21, {3, 7})])
def test_shor_factors_small_composites(N, expected_factors):
    result = factor_via_shor(N, counting_qubits=8, shots=2048, seed=42)
    assert result.success
    assert set(result.factors) == expected_factors
    assert result.data_label == "QUANTUM SIMULATION"


def test_shor_even_n_uses_classical_shortcut():
    result = factor_via_shor(16)
    assert result.classical_shortcut_used
    assert result.factors == (2, 8)


def test_shor_rejects_n_requiring_too_many_qubits():
    with pytest.raises(ValueError):
        factor_via_shor(2 ** 40 + 1, counting_qubits=8)


def test_shor_caveat_never_claims_rsa_broken():
    result = factor_via_shor(15)
    lowered = result.caveat.lower()
    assert "does not demonstrate breaking rsa" in lowered or "not demonstrate breaking rsa" in lowered

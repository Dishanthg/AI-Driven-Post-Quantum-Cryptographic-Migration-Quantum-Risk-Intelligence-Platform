from __future__ import annotations

import pytest

from app.crypto import registry as algo_registry


def test_all_specs_have_valid_classification():
    valid = {algo_registry.CLASSICAL_PK, algo_registry.CLASSICAL_SYM, algo_registry.HASH,
             algo_registry.PQC_KEM, algo_registry.PQC_SIG, algo_registry.HYBRID}
    for spec in algo_registry.all_specs():
        assert spec.classification in valid, f"{spec.id} has invalid classification {spec.classification!r}"


def test_all_specs_have_valid_quantum_vulnerability():
    valid = {algo_registry.QUANTUM_VULNERABLE, algo_registry.QUANTUM_WEAKENED, algo_registry.NOT_SIGNIFICANTLY_AFFECTED}
    for spec in algo_registry.all_specs():
        assert spec.quantum_vulnerability in valid


def test_classical_public_key_algorithms_are_quantum_vulnerable():
    for spec in algo_registry.list_by_classification(algo_registry.CLASSICAL_PK):
        assert spec.quantum_vulnerability == algo_registry.QUANTUM_VULNERABLE


def test_pqc_algorithms_not_significantly_affected():
    for classification in (algo_registry.PQC_KEM, algo_registry.PQC_SIG, algo_registry.HYBRID):
        for spec in algo_registry.list_by_classification(classification):
            assert spec.quantum_vulnerability == algo_registry.NOT_SIGNIFICANTLY_AFFECTED


def test_get_unknown_algorithm_raises():
    with pytest.raises(KeyError):
        algo_registry.get("NOT-A-REAL-ALGORITHM")


def test_get_by_provider_key_roundtrips():
    spec = algo_registry.get("ML-KEM-768")
    assert algo_registry.get_by_provider_key(spec.provider_key).id == "ML-KEM-768"


def test_get_by_provider_key_unknown_raises():
    with pytest.raises(KeyError):
        algo_registry.get_by_provider_key("not-a-real-provider-key")


def test_every_operable_spec_has_a_working_provider():
    from app.crypto.providers import get_provider
    for spec in algo_registry.all_specs():
        if spec.provider_key:
            get_provider(spec.provider_key)  # must not raise

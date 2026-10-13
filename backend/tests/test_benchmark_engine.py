from __future__ import annotations

import pytest

from app.benchmarks.engine import benchmark_kem, benchmark_keygen, benchmark_signature


def test_benchmark_keygen_produces_correct_iteration_count():
    summary = benchmark_keygen("ecdsa_p256", iterations=10, warmup=1)
    assert summary.iterations == 10
    assert len(summary.timings_ms) == 10
    assert all(t >= 0 for t in summary.timings_ms)
    assert summary.mean_ms >= 0
    assert summary.ci95_low_ms <= summary.mean_ms <= summary.ci95_high_ms + 1e-6


def test_benchmark_kem_rejects_non_kem_provider():
    with pytest.raises(ValueError):
        benchmark_kem("ecdsa_p256", iterations=5)


def test_benchmark_signature_rejects_non_signing_provider():
    with pytest.raises(ValueError):
        benchmark_signature("ml_kem_768", iterations=5)


def test_benchmark_kem_records_real_sizes():
    result = benchmark_kem("ml_kem_768", iterations=5, warmup=1)
    assert result["encapsulate"].public_key_bytes == 1184  # FIPS 203 ML-KEM-768 public key size
    assert result["encapsulate"].ciphertext_or_signature_bytes == 1088  # FIPS 203 ML-KEM-768 ciphertext size


def test_benchmark_environment_is_recorded():
    summary = benchmark_keygen("ecdsa_p256", iterations=3, warmup=0)
    assert summary.environment["python_version"]
    assert summary.environment["os"]

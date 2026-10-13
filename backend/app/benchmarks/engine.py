"""Reproducible cryptographic benchmarking engine (design doc Sections 16/17).

Every benchmark: runs N real iterations of a real CryptoProvider operation,
discards a warm-up iteration, records every per-iteration timing (not just a
summary), computes mean/median/stdev/percentiles/bootstrap CI, and captures the
execution environment. Nothing here is estimated, interpolated, or hard-coded -
`run_benchmark` always executes the operation on the current machine.
"""
from __future__ import annotations

import platform
import statistics
import time
from dataclasses import dataclass, field

import numpy as np

from app.crypto.providers import get_provider


@dataclass
class BenchmarkSummary:
    operation: str
    provider_key: str
    iterations: int
    timings_ms: list[float]
    mean_ms: float
    median_ms: float
    stdev_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    ci95_low_ms: float
    ci95_high_ms: float
    public_key_bytes: int | None = None
    ciphertext_or_signature_bytes: int | None = None
    environment: dict = field(default_factory=dict)


def _environment() -> dict:
    return {
        "cpu": platform.processor() or platform.machine(),
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "machine": platform.machine(),
    }


def _bootstrap_ci(samples: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    arr = np.array(samples)
    means = np.empty(n_boot)
    for i in range(n_boot):
        resample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = resample.mean()
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return lo, hi


def _summarize(operation: str, provider_key: str, timings_s: list[float], pk_bytes=None, out_bytes=None) -> BenchmarkSummary:
    ms = [t * 1000 for t in timings_s]
    ci_lo, ci_hi = _bootstrap_ci(ms)
    return BenchmarkSummary(
        operation=operation,
        provider_key=provider_key,
        iterations=len(ms),
        timings_ms=ms,
        mean_ms=statistics.mean(ms),
        median_ms=statistics.median(ms),
        stdev_ms=statistics.stdev(ms) if len(ms) > 1 else 0.0,
        p50_ms=float(np.percentile(ms, 50)),
        p95_ms=float(np.percentile(ms, 95)),
        p99_ms=float(np.percentile(ms, 99)),
        ci95_low_ms=ci_lo,
        ci95_high_ms=ci_hi,
        public_key_bytes=pk_bytes,
        ciphertext_or_signature_bytes=out_bytes,
        environment=_environment(),
    )


def benchmark_keygen(provider_key: str, iterations: int = 50, warmup: int = 3) -> BenchmarkSummary:
    provider = get_provider(provider_key)
    for _ in range(warmup):
        provider.generate_keypair()
    timings = []
    last_kp = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        last_kp = provider.generate_keypair()
        timings.append(time.perf_counter() - t0)
    return _summarize("keygen", provider_key, timings, pk_bytes=len(last_kp.public_key))


def benchmark_kem(provider_key: str, iterations: int = 50, warmup: int = 3) -> dict[str, BenchmarkSummary]:
    provider = get_provider(provider_key)
    if not provider.supports_kem:
        raise ValueError(f"{provider_key} does not support KEM operations")
    kp = provider.generate_keypair()
    for _ in range(warmup):
        ct, _ = provider.encapsulate(kp.public_key)
        provider.decapsulate(kp, ct)

    encap_timings, decap_timings = [], []
    last_ct = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        ct, _ss = provider.encapsulate(kp.public_key)
        encap_timings.append(time.perf_counter() - t0)
        last_ct = ct
        t0 = time.perf_counter()
        provider.decapsulate(kp, ct)
        decap_timings.append(time.perf_counter() - t0)

    return {
        "encapsulate": _summarize("encapsulate", provider_key, encap_timings, pk_bytes=len(kp.public_key), out_bytes=len(last_ct)),
        "decapsulate": _summarize("decapsulate", provider_key, decap_timings, pk_bytes=len(kp.public_key), out_bytes=len(last_ct)),
    }


def benchmark_signature(provider_key: str, iterations: int = 50, warmup: int = 3, message: bytes = b"quantumshield-benchmark-message") -> dict[str, BenchmarkSummary]:
    provider = get_provider(provider_key)
    if not provider.supports_sign:
        raise ValueError(f"{provider_key} does not support signing")
    kp = provider.generate_keypair()
    for _ in range(warmup):
        s = provider.sign(kp, message)
        provider.verify(kp.public_key, message, s)

    sign_timings, verify_timings = [], []
    last_sig = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        sig = provider.sign(kp, message)
        sign_timings.append(time.perf_counter() - t0)
        last_sig = sig
        t0 = time.perf_counter()
        provider.verify(kp.public_key, message, sig)
        verify_timings.append(time.perf_counter() - t0)

    return {
        "sign": _summarize("sign", provider_key, sign_timings, pk_bytes=len(kp.public_key), out_bytes=len(last_sig)),
        "verify": _summarize("verify", provider_key, verify_timings, pk_bytes=len(kp.public_key), out_bytes=len(last_sig)),
    }

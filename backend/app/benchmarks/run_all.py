"""Runs the full classical-vs-PQC benchmark sweep (design doc Section 16-18,
Experiment 1/2) across every operable algorithm in the CryptoProvider
registry, persists results to the DB, and writes a CSV summary under
research/tables/. `make benchmark`.
"""
from __future__ import annotations

import csv
import dataclasses
import datetime as dt

from app.benchmarks.engine import benchmark_kem, benchmark_keygen, benchmark_signature
from app.core.config import get_settings
from app.crypto import registry as algo_registry
from app.crypto.providers import get_provider
from app.db.models import Benchmark, BenchmarkRun
from app.db.session import SessionLocal

ITERATIONS = 30


def _persist(db, provider_key: str, algorithm_id: str, summary) -> None:
    benchmark = db.query(Benchmark).filter_by(name=f"{provider_key}_{summary.operation}", operation=summary.operation, algorithm_id=algorithm_id).one_or_none()
    if benchmark is None:
        benchmark = Benchmark(name=f"{provider_key}_{summary.operation}", operation=summary.operation, algorithm_id=algorithm_id)
        db.add(benchmark)
        db.flush()
    db.add(BenchmarkRun(
        benchmark_id=benchmark.id, iterations=summary.iterations, environment_json=summary.environment,
        started_at=dt.datetime.now(dt.UTC), completed_at=dt.datetime.now(dt.UTC),
        status="completed", raw_results_json={"timings_ms": summary.timings_ms},
        summary_stats_json=dataclasses.asdict(summary),
    ))


def run_sweep(iterations: int = ITERATIONS) -> list[dict]:
    db = SessionLocal()
    rows: list[dict] = []
    try:
        for spec in algo_registry.all_specs():
            if not spec.provider_key:
                continue
            provider = get_provider(spec.provider_key)

            keygen = benchmark_keygen(spec.provider_key, iterations=iterations)
            _persist(db, spec.provider_key, spec.id, keygen)
            row = {
                "algorithm_id": spec.id, "classification": spec.classification, "role": spec.role,
                "provider_key": spec.provider_key,
                "keygen_mean_ms": round(keygen.mean_ms, 4), "keygen_p95_ms": round(keygen.p95_ms, 4),
                "public_key_bytes": keygen.public_key_bytes,
            }

            if provider.supports_kem:
                kem = benchmark_kem(spec.provider_key, iterations=iterations)
                _persist(db, spec.provider_key, spec.id, kem["encapsulate"])
                _persist(db, spec.provider_key, spec.id, kem["decapsulate"])
                row.update({
                    "encapsulate_mean_ms": round(kem["encapsulate"].mean_ms, 4),
                    "decapsulate_mean_ms": round(kem["decapsulate"].mean_ms, 4),
                    "ciphertext_bytes": kem["encapsulate"].ciphertext_or_signature_bytes,
                })
            if provider.supports_sign:
                sig = benchmark_signature(spec.provider_key, iterations=iterations)
                _persist(db, spec.provider_key, spec.id, sig["sign"])
                _persist(db, spec.provider_key, spec.id, sig["verify"])
                row.update({
                    "sign_mean_ms": round(sig["sign"].mean_ms, 4),
                    "verify_mean_ms": round(sig["verify"].mean_ms, 4),
                    "signature_bytes": sig["sign"].ciphertext_or_signature_bytes,
                })
            rows.append(row)
        db.commit()
    finally:
        db.close()
    return rows


def write_csv(rows: list[dict], out_path) -> None:
    if not rows:
        return
    fieldnames = sorted({k for r in rows for k in r}, key=lambda k: (k != "algorithm_id", k))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    settings = get_settings()
    results = run_sweep()
    out = settings.research_dir / "tables" / "benchmark_sweep.csv"
    write_csv(results, out)
    print(f"Benchmarked {len(results)} algorithms ({ITERATIONS} iterations each). Wrote {out}")
    for r in results:
        extra = ""
        if "encapsulate_mean_ms" in r:
            extra = f"encaps={r['encapsulate_mean_ms']:.4f}ms"
        elif "sign_mean_ms" in r:
            extra = f"sign={r['sign_mean_ms']:.4f}ms"
        print(f"  {r['algorithm_id']:26s} keygen={r['keygen_mean_ms']:>9.4f}ms  {extra}")

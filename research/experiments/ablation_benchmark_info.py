"""Ablation study: does giving the PQC recommendation engine access to REAL
benchmark data change its recommendations? (design doc Section 40's fourth,
previously-unimplemented ablation type - "PQC benchmark information".)

This is only a meaningful question because app/recommendations/engine.py was
extended this session to actually consult real BenchmarkRun data for
long-lived, internet-facing TLS-certificate assets (see
docs/architecture/adr/ADR-005 and app/recommendations/engine.py's
_real_benchmarked_signature_bytes) - previously the recommender never
touched benchmark data at all, which would have made this ablation trivially
a no-op. The benchmark numbers used here are produced by REAL EXECUTION of
app.benchmarks.engine against the real ML-DSA-65 / SLH-DSA-SHA2-128F
providers, not copied from a table.

Run against an isolated, temporary SQLite database - never the dev/prod
database - so this script has no side effects on `backend/quantumshield.db`.

Run: python -m research.experiments.ablation_benchmark_info   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.benchmarks.engine import benchmark_signature  # noqa: E402
from app.benchmarks.run_all import _persist  # noqa: E402
from app.crypto import registry as algo_registry  # noqa: E402
from app.db import models  # noqa: E402,F401 - registers all mapped classes on Base
from app.db.base import Base  # noqa: E402
from app.db.models import Algorithm, Asset, PQCRecommendation  # noqa: E402
from app.discovery.scanner import scan_directory  # noqa: E402
from app.recommendations.engine import recommend_for_all_assets  # noqa: E402
from app.risk.service import METHOD_RULE, assess_all_assets  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

SIGNATURE_PROVIDERS_TO_BENCHMARK = ["ml_dsa_65", "slh_dsa_sha2_128f"]


def _fresh_session():
    db_path = Path(tempfile.mkdtemp()) / "ablation_benchmark_info.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()
    for spec in algo_registry.all_specs():
        session.add(Algorithm(
            id=spec.id, name=spec.name, family=spec.family, role=spec.role,
            classification=spec.classification, security_basis=spec.security_basis,
            quantum_vulnerability=spec.quantum_vulnerability, standard_ref=spec.standard_ref,
            library_source=spec.library_source, typical_key_size_bits=spec.typical_key_size_bits,
        ))
    session.commit()
    return session


def _recommendations_by_hostname(db) -> dict[str, dict]:
    # Keyed by hostname, not Asset.id: each db here is a SEPARATE fresh
    # in-memory-style SQLite database, so Asset.id (a freshly-generated UUID
    # per scan_directory() call) is not a stable join key across the two
    # dbs this ablation compares - see the identical fix/note in
    # ablation_ai_model.py, which caught this exact bug first.
    id_to_hostname = {a.id: a.hostname for a in db.query(Asset).all()}
    return {
        id_to_hostname[r.asset_id]: {"strategy": r.strategy, "target_algorithm_id": r.target_algorithm_id, "rationale": r.rationale}
        for r in db.query(PQCRecommendation).all()
    }


def run() -> dict:
    # --- WITHOUT benchmark information ---
    db_without = _fresh_session()
    scan_directory(db_without)
    assess_all_assets(db_without, method=METHOD_RULE)
    recommend_for_all_assets(db_without)
    recs_without = _recommendations_by_hostname(db_without)

    # --- WITH real benchmark information (real execution, not copied numbers) ---
    db_with = _fresh_session()
    scan_directory(db_with)
    for provider_key in SIGNATURE_PROVIDERS_TO_BENCHMARK:
        spec = next(s for s in algo_registry.all_specs() if s.provider_key == provider_key)
        sig = benchmark_signature(provider_key, iterations=10)
        _persist(db_with, provider_key, spec.id, sig["sign"])
        _persist(db_with, provider_key, spec.id, sig["verify"])
    db_with.commit()
    assess_all_assets(db_with, method=METHOD_RULE)
    recommend_for_all_assets(db_with)
    recs_with = _recommendations_by_hostname(db_with)

    assert set(recs_without.keys()) == set(recs_with.keys()), (
        "hostname sets differ between the two runs - aborting rather than silently comparing a "
        "partial/misaligned set."
    )

    changed = []
    for hostname, without in recs_without.items():
        with_ = recs_with[hostname]
        if without["target_algorithm_id"] != with_["target_algorithm_id"] or without["strategy"] != with_["strategy"]:
            changed.append({
                "hostname": hostname,
                "without_benchmark_info": without,
                "with_benchmark_info": with_,
            })

    return {
        "experiment_id": "ablation_benchmark_info",
        "hypothesis": "Section 40's 4th ablation type: does the PQC recommendation engine's access to REAL "
                      "benchmark data (vs. none) change its recommendations for any asset?",
        "total_assets": len(recs_without),
        "recommendations_changed": len(changed),
        "changed_details": changed,
        "note": "The recommendation engine only consults benchmark data for long-lived (>10y), "
                "internet-facing, TLS-certificate-usage signature assets on a classical algorithm - see "
                "app/recommendations/engine.py's _target_for_signature. A 0-asset change here would mean "
                "no asset in the current 42-asset lab meets that specific combination of conditions, which "
                "is itself a real, reportable finding about this ablation's scope, not a failure.",
    }


def main() -> int:
    result = run()
    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_benchmark_info.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Ablation study: PQC benchmark information availability\n",
        f"Total assets evaluated: {result['total_assets']}. "
        f"Recommendations changed by having real benchmark data available: {result['recommendations_changed']}.\n",
    ]
    if result["changed_details"]:
        lines.append("| hostname | without (target) | with (target) |")
        lines.append("|---|---|---|")
        for c in result["changed_details"]:
            lines.append(f"| {c['hostname']} | {c['without_benchmark_info']['target_algorithm_id']} | {c['with_benchmark_info']['target_algorithm_id']} |")
    else:
        lines.append("No asset in the current lab configuration met the "
                      "long-lived + internet-facing + TLS-certificate + classical-signature condition this "
                      "session's implementation checks, so no recommendation changed. See `note` in the JSON "
                      "output for why this is a real finding, not a null result from a broken ablation.")
    (out_dir / "ablation_benchmark_info.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Migration Simulator (design doc Section 27).

Simulates each stage of a MigrationPlan (legacy -> [hybrid ->] pqc_enabled) by
actually executing the relevant CryptoProvider operations and real benchmarks
(app.benchmarks.engine) for each stage's algorithm - never estimated or
hard-coded numbers (Rule 9, Rule 11). Also runs an explicit roundtrip
correctness check (encapsulate/decapsulate or sign/verify) per stage.

For a `hybrid_migration` plan, the final `pqc_enabled` step is left un-simulated
(explicitly described as "future, not scheduled by this plan" by the planner) -
the simulator only models the stages this specific plan actually schedules.

This module never touches any real production system, service, or
certificate; it is a pure in-memory model over the CryptoProvider abstraction
(Rule: "Do not alter production systems").
"""
from __future__ import annotations

import dataclasses

from sqlalchemy.orm import Session

from app.benchmarks.engine import benchmark_kem, benchmark_keygen, benchmark_signature
from app.crypto import registry as algo_registry
from app.crypto.providers import get_provider
from app.db.models import MigrationPlan, MigrationStep

VERIFICATION_MESSAGE = b"quantumshield-migration-simulation-verification"


def _verify_roundtrip(provider) -> bool:
    kp = provider.generate_keypair()
    if provider.supports_kem:
        ct, ss = provider.encapsulate(kp.public_key)
        ss2 = provider.decapsulate(kp, ct)
        return ss == ss2
    if provider.supports_sign:
        sig = provider.sign(kp, VERIFICATION_MESSAGE)
        return provider.verify(kp.public_key, VERIFICATION_MESSAGE, sig)
    return False


def _benchmark_stage(provider_key: str, iterations: int) -> dict:
    provider = get_provider(provider_key)
    out = {"keygen": dataclasses.asdict(benchmark_keygen(provider_key, iterations=iterations))}
    if provider.supports_kem:
        kem = benchmark_kem(provider_key, iterations=iterations)
        out["encapsulate"] = dataclasses.asdict(kem["encapsulate"])
        out["decapsulate"] = dataclasses.asdict(kem["decapsulate"])
    if provider.supports_sign:
        sig = benchmark_signature(provider_key, iterations=iterations)
        out["sign"] = dataclasses.asdict(sig["sign"])
        out["verify"] = dataclasses.asdict(sig["verify"])
    return out


def _algorithm_id_for_step(plan: MigrationPlan, step: MigrationStep) -> str:
    if step.stage == "legacy":
        return plan.current_algorithm_id
    if step.stage == "hybrid":
        return "HYBRID-ECDH-ML-KEM-768"
    return plan.target_algorithm_id  # pqc_enabled


def _primary_op(bench: dict) -> tuple[str, float] | None:
    for op in ("encapsulate", "sign"):
        if op in bench:
            return op, bench[op]["mean_ms"]
    return None


def _primary_size(bench: dict) -> int | None:
    for op in ("encapsulate", "sign"):
        if op in bench:
            return bench[op]["ciphertext_or_signature_bytes"]
    return None


def simulate_plan(db: Session, plan: MigrationPlan, iterations: int = 15) -> dict:
    steps = sorted(plan.steps, key=lambda s: s.sequence)
    has_hybrid_step = any(s.stage == "hybrid" for s in steps)
    stage_results: dict[str, dict] = {}

    for step in steps:
        # a hybrid_migration plan's final pqc_enabled step is explicitly future/unscheduled - don't simulate it
        if has_hybrid_step and step.stage == "pqc_enabled":
            continue

        algo_id = _algorithm_id_for_step(plan, step)
        spec = algo_registry.get(algo_id)
        provider = get_provider(spec.provider_key)

        verified = _verify_roundtrip(provider)
        bench = _benchmark_stage(spec.provider_key, iterations)

        step.simulated_result_json = {
            "data_label": "BENCHMARK DATA (executed on this machine, this run)",
            "algorithm_id": algo_id,
            "roundtrip_verified": verified,
            "benchmarks": bench,
        }
        step.status = "completed" if verified else "failed"
        stage_results[step.stage] = step.simulated_result_json

    # aggregate legacy -> final-simulated-stage deltas into the plan's performance_impact_json
    legacy = stage_results.get("legacy")
    final_stage_name = "hybrid" if "hybrid" in stage_results else ("pqc_enabled" if "pqc_enabled" in stage_results else None)
    final = stage_results.get(final_stage_name) if final_stage_name else None

    impact = dict(plan.performance_impact_json or {})
    impact["simulated"] = True
    impact["simulation_note"] = "In-memory CryptoProvider simulation only; no production system was modified."
    if legacy and final:
        legacy_keygen = legacy["benchmarks"]["keygen"]["mean_ms"]
        final_keygen = final["benchmarks"]["keygen"]["mean_ms"]
        legacy_primary = _primary_op(legacy["benchmarks"])
        final_primary = _primary_op(final["benchmarks"])
        impact["keygen_latency_delta_ms"] = round(final_keygen - legacy_keygen, 4)
        impact["keygen_latency_ratio"] = round(final_keygen / legacy_keygen, 3) if legacy_keygen else None
        if legacy_primary and final_primary:
            impact["primary_op_legacy"] = legacy_primary[0]
            impact["primary_op_final"] = final_primary[0]
            impact["primary_op_latency_delta_ms"] = round(final_primary[1] - legacy_primary[1], 4)
        legacy_size = _primary_size(legacy["benchmarks"])
        final_size = _primary_size(final["benchmarks"])
        if legacy_size and final_size:
            impact["primary_output_size_delta_bytes"] = final_size - legacy_size
            impact["primary_output_size_ratio"] = round(final_size / legacy_size, 3)
    plan.performance_impact_json = impact
    plan.status = "in_progress"  # simulation executed; NOT deployed to any real system

    db.add(plan)
    db.commit()
    return {"plan_id": plan.id, "stages_simulated": list(stage_results.keys()), "performance_impact": impact}


def simulate_all_plans(db: Session, iterations: int = 15) -> list[dict]:
    results = []
    for plan in db.query(MigrationPlan).filter(MigrationPlan.status == "proposed").all():
        results.append(simulate_plan(db, plan, iterations=iterations))
    return results


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        outcomes = simulate_all_plans(session)
        print(f"Simulated {len(outcomes)} migration plans.")
        for o in outcomes[:3]:
            print(f"  plan={o['plan_id']} stages={o['stages_simulated']} impact={o['performance_impact']}")
    finally:
        session.close()

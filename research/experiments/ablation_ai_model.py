"""Ablation study: does having a trained AI model in the risk-assessment
step (vs. only the deterministic rule baseline) change what the platform
recommends downstream? (design doc Section 40's "AI model" ablation.)

This is a systems-level ablation, distinct from Experiment 3's classifier
metric comparison (macro-F1 etc. on a held-out synthetic-label test set):
here we run the REAL discover -> assess -> recommend -> plan pipeline twice
against the same 42-asset lab, once with method="ml_model" and once with
method="rule_baseline", and measure how many assets end up with a different
PQC recommendation strategy or a different migration-plan priority as a
downstream consequence of which risk-assessment method fed the recommender.

Uses an isolated, temporary SQLite database - never the dev/prod database.

Run: python -m research.experiments.ablation_ai_model   (repo root, .venv active)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.crypto import registry as algo_registry  # noqa: E402
from app.db import models  # noqa: E402,F401 - registers all mapped classes on Base
from app.db.base import Base  # noqa: E402
from app.db.models import Algorithm, Asset, MigrationPlan, PQCRecommendation  # noqa: E402
from app.discovery.scanner import scan_directory  # noqa: E402
from app.migration.planner import plan_for_all_recommendations  # noqa: E402
from app.recommendations.engine import recommend_for_all_assets  # noqa: E402
from app.risk.service import METHOD_ML, METHOD_RULE, assess_all_assets  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def _fresh_session():
    db_path = Path(tempfile.mkdtemp()) / "ablation_ai_model.db"
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


def _run_pipeline(method: str) -> dict:
    # NOTE: Asset.id is a freshly-generated UUID on every scan_directory() call
    # against a fresh database, so it is NOT a stable join key across the two
    # separate pipeline runs this ablation compares. hostname (deterministic,
    # sourced from the lab config files) is used instead. An earlier version
    # of this script joined on asset_id and silently found "0 changes" for
    # every asset because the join never matched anything - a false negative
    # from a broken comparison, not a real finding; see
    # research/RESEARCH_LOG.md for the caught-and-fixed record.
    db = _fresh_session()
    scan_directory(db)
    assess_all_assets(db, method=method)
    recommend_for_all_assets(db)
    plans = plan_for_all_recommendations(db)

    id_to_hostname = {a.id: a.hostname for a in db.query(Asset).all()}
    recs = {
        id_to_hostname[r.asset_id]: {"strategy": r.strategy, "target_algorithm_id": r.target_algorithm_id}
        for r in db.query(PQCRecommendation).all()
    }
    plan_priorities = {id_to_hostname[p.asset_id]: p.priority for p in db.query(MigrationPlan).all()}
    return {"recommendations": recs, "plan_priorities": plan_priorities, "n_plans": len(plans)}


def run() -> dict:
    with_ml = _run_pipeline(METHOD_ML)
    with_rule = _run_pipeline(METHOD_RULE)

    assert set(with_ml["recommendations"].keys()) == set(with_rule["recommendations"].keys()), (
        "hostname sets differ between the two pipeline runs - the lab config didn't scan identically; "
        "aborting rather than silently comparing a partial/misaligned set."
    )

    rec_changed = []
    for hostname, ml_rec in with_ml["recommendations"].items():
        rule_rec = with_rule["recommendations"][hostname]
        if ml_rec["strategy"] != rule_rec["strategy"] or ml_rec["target_algorithm_id"] != rule_rec["target_algorithm_id"]:
            rec_changed.append({"hostname": hostname, "ml_model": ml_rec, "rule_baseline": rule_rec})

    priority_changed = []
    for hostname, ml_prio in with_ml["plan_priorities"].items():
        rule_prio = with_rule["plan_priorities"].get(hostname)
        if rule_prio is not None and ml_prio != rule_prio:
            priority_changed.append({"hostname": hostname, "ml_model_priority": ml_prio, "rule_baseline_priority": rule_prio})

    total_assets = len(with_ml["recommendations"])
    return {
        "experiment_id": "ablation_ai_model",
        "hypothesis": "Section 40's 'AI model' ablation: does using the trained ML risk model (vs. only the "
                      "deterministic rule baseline) change downstream PQC recommendations or migration-plan "
                      "priorities, when run through the real end-to-end pipeline on the 42-asset lab?",
        "total_assets": total_assets,
        "recommendations_changed": len(rec_changed),
        "recommendations_changed_pct": round(100 * len(rec_changed) / total_assets, 1) if total_assets else 0.0,
        "migration_plan_priority_changed": len(priority_changed),
        "n_plans_with_ml": with_ml["n_plans"],
        "n_plans_with_rule": with_rule["n_plans"],
        "recommendation_changes_detail": rec_changed,
        "priority_changes_detail": priority_changed,
    }


def main() -> int:
    result = run()
    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_ai_model.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Ablation study: AI model vs. rule baseline (systems-level, downstream impact)\n",
        f"Total assets: {result['total_assets']}. Recommendations changed: "
        f"{result['recommendations_changed']} ({result['recommendations_changed_pct']}%). "
        f"Migration-plan priority changed: {result['migration_plan_priority_changed']}. "
        f"Plans built with ML-fed risk: {result['n_plans_with_ml']}; with rule-fed risk: {result['n_plans_with_rule']}.\n",
    ]
    if result["recommendation_changes_detail"]:
        lines.append("| hostname | ML-fed strategy/target | rule-fed strategy/target |")
        lines.append("|---|---|---|")
        for c in result["recommendation_changes_detail"][:20]:
            lines.append(f"| {c['hostname']} | {c['ml_model']['strategy']}/{c['ml_model']['target_algorithm_id']} | {c['rule_baseline']['strategy']}/{c['rule_baseline']['target_algorithm_id']} |")
    (out_dir / "ablation_ai_model.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_detail")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

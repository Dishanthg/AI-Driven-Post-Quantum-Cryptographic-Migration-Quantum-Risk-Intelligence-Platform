"""End-to-end demonstration (design doc Section 30 / `make demo`).

Runs the full pipeline against a fresh database:
  1. apply Alembic migrations
  2. seed the algorithm registry + demo user accounts
  3. discover cryptographic assets from enterprise_lab/configs/
  4. train the AI risk model (skipped if a trained model already exists,
     unless --retrain is passed) and sync its version into the DB
  5. assess quantum risk for every discovered asset (real ML inference)
  6. generate PQC recommendations for every asset
  7. build migration plans for every actionable recommendation
  8. simulate every migration plan (real CryptoProvider benchmarks + roundtrip
     verification)
  9. print a summary report

No numbers here are hard-coded: every count and metric printed is read back
from what the pipeline actually produced this run.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _run_alembic_upgrade() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrain", action="store_true", help="retrain the AI risk model even if an artifact already exists")
    args = parser.parse_args()

    print("=" * 70)
    print("QUANTUMSHIELD END-TO-END DEMONSTRATION")
    print("=" * 70)

    print("\n[1/9] Applying database migrations...")
    _run_alembic_upgrade()

    from app.db.seed import main as seed_algorithms
    from app.db.seed_users import main as seed_users
    from app.db.session import SessionLocal

    print("\n[2/9] Seeding algorithm registry + demo accounts...")
    seed_algorithms()
    seed_users()

    db = SessionLocal()
    try:
        print("\n[3/9] Discovering cryptographic assets from enterprise_lab/configs/...")
        from app.discovery.scanner import scan_directory
        scan = scan_directory(db)
        print(f"  -> {scan.applications_seen} applications, {scan.assets_created} created / {scan.assets_updated} updated, {len(scan.errors)} errors")

        print("\n[4/9] Training AI risk model (rule baseline vs LogReg/RandomForest/XGBoost)...")
        from app.core.config import get_settings
        settings = get_settings()
        model_dir = settings.model_registry_dir / "risk_prioritization"
        if args.retrain or not model_dir.exists() or not any(model_dir.iterdir()):
            from app.ai.train import train_and_evaluate
            train_out = train_and_evaluate()
            print(f"  -> best model: {train_out['best_model']} (version {train_out['version']})")
            for name in ("rule_baseline", "logistic_regression", "random_forest", "xgboost"):
                m = train_out["results"][name]
                print(f"     {name:22s} macro_f1={m['macro_f1']:.4f}")
        else:
            print("  -> using existing trained model artifact (pass --retrain to force retraining)")

        from app.ai.model_registry import sync_model_versions_to_db
        sync_model_versions_to_db(db)

        print("\n[5/9] Assessing quantum risk for every asset (ML model + SHAP)...")
        from app.risk.service import assess_all_assets
        assessments = assess_all_assets(db, method="ml_model")
        by_priority: dict[str, int] = {}
        for a in assessments:
            by_priority[a.priority] = by_priority.get(a.priority, 0) + 1
        print(f"  -> {len(assessments)} assets assessed. Priority distribution: {by_priority}")

        print("\n[6/9] Generating PQC migration recommendations...")
        from app.recommendations.engine import recommend_for_all_assets
        recs = recommend_for_all_assets(db)
        by_strategy: dict[str, int] = {}
        for r in recs:
            by_strategy[r.strategy] = by_strategy.get(r.strategy, 0) + 1
        print(f"  -> {len(recs)} recommendations. Strategy distribution: {by_strategy}")

        print("\n[7/9] Building migration plans...")
        from app.migration.planner import plan_for_all_recommendations
        plans = plan_for_all_recommendations(db)
        total_hours = sum(p.estimated_effort_hours for p in plans)
        print(f"  -> {len(plans)} migration plans, {total_hours:.1f} estimated hours total")

        print("\n[8/9] Simulating migrations (real CryptoProvider benchmarks + roundtrip verification)...")
        from app.migration.simulator import simulate_all_plans
        outcomes = simulate_all_plans(db, iterations=10)
        print(f"  -> {len(outcomes)} plans simulated")

        print("\n[9/9] Summary")
        print("-" * 70)
        from app.db.models import Asset, MigrationPlan, PQCRecommendation, RiskAssessment
        print(f"  Total cryptographic assets discovered : {db.query(Asset).count()}")
        print(f"  Risk assessments on record            : {db.query(RiskAssessment).count()}")
        print(f"  PQC recommendations on record          : {db.query(PQCRecommendation).count()}")
        print(f"  Migration plans on record               : {db.query(MigrationPlan).count()}")
        print(f"  Migration plans simulated this run       : {len(outcomes)}")
        print("-" * 70)
        print("Start the API to explore results: uvicorn app.main:app --reload --app-dir backend")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()

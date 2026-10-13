"""Syncs trained model artifacts on disk (produced by app.ai.train) into the
`models` / `model_versions` DB tables (design doc Section 56: model
versioning). The artifact directory on disk remains the source of truth for
the actual weights; this just makes versions queryable/auditable from the
relational schema and lets a RiskAssessment row reference the exact
model_version_id that produced it.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import MLModel, ModelVersion


def sync_model_versions_to_db(db: Session, model_name: str = "risk_prioritization") -> list[ModelVersion]:
    settings = get_settings()
    base = settings.model_registry_dir / model_name
    if not base.exists():
        return []

    model = db.query(MLModel).filter_by(name=model_name).one_or_none()
    if model is None:
        model = MLModel(name=model_name)
        db.add(model)
        db.flush()

    synced = []
    for version_dir in sorted(base.iterdir()):
        if not version_dir.is_dir():
            continue
        metadata_path = version_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text())

        existing = db.query(ModelVersion).filter_by(model_id=model.id, version=metadata["version"]).one_or_none()
        if existing:
            synced.append(existing)
            continue

        mv = ModelVersion(
            model_id=model.id,
            version=metadata["version"],
            algorithm=metadata["algorithm"],
            features_json={"features": metadata["features"]},
            hyperparameters_json={},
            dataset_ref=metadata["dataset_ref"],
            random_seed=metadata["random_seed"],
            metrics_json=metadata["metrics"],
            artifact_path=str(version_dir),
            is_active=False,
        )
        db.add(mv)
        synced.append(mv)

    # activate only the most recent version
    db.flush()
    all_versions = db.query(ModelVersion).filter_by(model_id=model.id).order_by(ModelVersion.version).all()
    for v in all_versions:
        v.is_active = False
    if all_versions:
        all_versions[-1].is_active = True
    db.commit()
    return synced


def get_active_model_version(db: Session, model_name: str = "risk_prioritization") -> ModelVersion | None:
    model = db.query(MLModel).filter_by(name=model_name).one_or_none()
    if model is None:
        return None
    return db.query(ModelVersion).filter_by(model_id=model.id, is_active=True).one_or_none()


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        versions = sync_model_versions_to_db(session)
        print(f"Synced {len(versions)} model version(s) to DB.")
    finally:
        session.close()

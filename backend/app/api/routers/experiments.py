from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_viewer
from app.db.models import Experiment, ExperimentRun

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.get("")
def list_experiments(db: Session = Depends(get_db), _=Depends(require_viewer)):
    experiments = db.query(Experiment).all()
    return [
        {
            "experiment_id": e.experiment_id, "hypothesis": e.hypothesis, "description": e.description,
            "run_count": db.query(ExperimentRun).filter_by(experiment_id=e.id).count(),
        }
        for e in experiments
    ]


@router.get("/{experiment_id}/runs")
def list_experiment_runs(experiment_id: str, db: Session = Depends(get_db), _=Depends(require_viewer)):
    exp = db.query(Experiment).filter_by(experiment_id=experiment_id).one_or_none()
    if exp is None:
        return []
    runs = db.query(ExperimentRun).filter_by(experiment_id=exp.id).order_by(ExperimentRun.started_at.desc()).all()
    return [
        {
            "id": r.id, "seed": r.seed, "git_commit": r.git_commit, "status": r.status,
            "started_at": r.started_at.isoformat(), "results": r.results_json,
        }
        for r in runs
    ]

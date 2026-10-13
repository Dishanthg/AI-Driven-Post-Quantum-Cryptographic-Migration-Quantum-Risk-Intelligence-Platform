# NOTE: no `from __future__ import annotations` in this file - slowapi's
# @limiter.limit decorator on grover_run/shor_run breaks FastAPI's signature
# introspection when combined with postponed (string) annotations. See
# app/api/routers/auth.py's identical note for the full explanation.
import dataclasses

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import GroverRunRequest, ShorRunRequest
from app.core.config import get_settings
from app.core.metrics import QUANTUM_RUNS
from app.core.rate_limit import EXPENSIVE_LIMIT, limiter
from app.core.security import CurrentUser
from app.db.models import QuantumExperiment, QuantumRun
from app.quantum.grover_lab import run_grover
from app.quantum.shor_lab import factor_via_shor

router = APIRouter(prefix="/api/v1/quantum", tags=["quantum"])


def _get_or_create_experiment(db: Session, name: str, kind: str, config: dict) -> QuantumExperiment:
    existing = db.query(QuantumExperiment).filter_by(name=name, kind=kind).one_or_none()
    if existing:
        return existing
    exp = QuantumExperiment(name=name, kind=kind, config_json=config)
    db.add(exp)
    db.flush()
    return exp


@router.post("/grover/run")
@limiter.limit(EXPENSIVE_LIMIT)
def grover_run(request: Request, response: Response, req: GroverRunRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    settings = get_settings()
    if req.n_qubits > settings.quantum_max_qubits:
        raise HTTPException(status_code=422, detail=f"n_qubits capped at {settings.quantum_max_qubits} (lab scope limit, see ADR-006)")
    try:
        result = run_grover(req.n_qubits, req.marked_states, shots=req.shots, seed=req.seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    experiment = _get_or_create_experiment(db, name="grover_search", kind="grover", config={"n_qubits": req.n_qubits})
    run = QuantumRun(
        experiment_id=experiment.id, backend=result.backend, noise_model="ideal",
        qubits=result.n_qubits, circuit_depth=result.circuit_depth, shots=result.shots,
        runtime_seconds=result.runtime_seconds, success_probability=result.success_probability,
        result_json=dataclasses.asdict(result), is_real_hardware=False,
    )
    db.add(run)
    db.commit()
    QUANTUM_RUNS.labels("grover").inc()
    record_audit(db, actor=user.username, action="quantum_grover_run", target_type="quantum_run", target_id=run.id,
                 after={"success_probability": result.success_probability, "n_qubits": result.n_qubits})
    return dataclasses.asdict(result)


@router.post("/shor/run")
@limiter.limit(EXPENSIVE_LIMIT)
def shor_run(request: Request, response: Response, req: ShorRunRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    try:
        result = factor_via_shor(req.N, a=req.a, counting_qubits=req.counting_qubits, shots=req.shots, seed=req.seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    experiment = _get_or_create_experiment(db, name="shor_factoring", kind="shor", config={"N": req.N})
    run = QuantumRun(
        experiment_id=experiment.id, backend=result.backend, noise_model="ideal",
        qubits=result.total_qubits, circuit_depth=result.circuit_depth, shots=result.shots,
        runtime_seconds=result.runtime_seconds, success_probability=1.0 if result.success else 0.0,
        result_json=dataclasses.asdict(result), is_real_hardware=False,
    )
    db.add(run)
    db.commit()
    QUANTUM_RUNS.labels("shor").inc()
    record_audit(db, actor=user.username, action="quantum_shor_run", target_type="quantum_run", target_id=run.id,
                 after={"N": result.N, "factors": result.factors, "success": result.success})
    return dataclasses.asdict(result)


@router.get("/runs")
def list_runs(kind: str | None = None, db: Session = Depends(get_db), _=Depends(require_viewer)):
    q = db.query(QuantumRun).join(QuantumExperiment)
    if kind:
        q = q.filter(QuantumExperiment.kind == kind)
    runs = q.order_by(QuantumRun.created_at.desc()).limit(100).all()
    return [
        {
            "id": r.id, "backend": r.backend, "qubits": r.qubits, "circuit_depth": r.circuit_depth,
            "shots": r.shots, "runtime_seconds": r.runtime_seconds, "success_probability": r.success_probability,
            "is_real_hardware": r.is_real_hardware, "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]

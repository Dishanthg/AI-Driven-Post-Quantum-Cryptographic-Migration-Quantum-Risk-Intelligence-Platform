# NOTE: no `from __future__ import annotations` in this file - slowapi's
# @limiter.limit decorator on run_benchmark breaks FastAPI's signature
# introspection when combined with postponed (string) annotations. See
# app/api/routers/auth.py's identical note for the full explanation.
import dataclasses
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import get_db, require_analyst, require_viewer
from app.api.schemas import BenchmarkRunRequest, BenchmarkSummaryOut
from app.benchmarks.engine import benchmark_kem, benchmark_keygen, benchmark_signature
from app.core.metrics import BENCHMARK_RUNS
from app.core.rate_limit import EXPENSIVE_LIMIT, limiter
from app.core.security import CurrentUser
from app.crypto import registry as algo_registry
from app.db.models import Benchmark, BenchmarkRun

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])

_MAX_ITERATIONS = 500  # a benchmark run is real, executed work - cap it so an API caller can't request an
# hours-long run (design doc Section 68: "Do not run expensive benchmark suites on every pull request")


def _get_or_create_benchmark(db: Session, name: str, operation: str, algorithm_id: str) -> Benchmark:
    existing = db.query(Benchmark).filter_by(name=name, operation=operation, algorithm_id=algorithm_id).one_or_none()
    if existing:
        return existing
    b = Benchmark(name=name, operation=operation, algorithm_id=algorithm_id)
    db.add(b)
    db.flush()
    return b


def _persist_run(db: Session, benchmark: Benchmark, summary) -> BenchmarkRun:
    run = BenchmarkRun(
        benchmark_id=benchmark.id,
        iterations=summary.iterations,
        environment_json=summary.environment,
        started_at=dt.datetime.now(dt.UTC),
        completed_at=dt.datetime.now(dt.UTC),
        status="completed",
        raw_results_json={"timings_ms": summary.timings_ms},
        summary_stats_json=dataclasses.asdict(summary),
    )
    db.add(run)
    db.flush()
    return run


@router.post("/run", response_model=list[BenchmarkSummaryOut])
@limiter.limit(EXPENSIVE_LIMIT)
def run_benchmark(request: Request, response: Response, req: BenchmarkRunRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(require_analyst)):
    if req.iterations < 1 or req.iterations > _MAX_ITERATIONS:
        raise HTTPException(status_code=422, detail=f"iterations must be in [1, {_MAX_ITERATIONS}]")
    try:
        spec = algo_registry.get_by_provider_key(req.provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    summaries = []
    if req.operation == "keygen":
        summaries = [benchmark_keygen(req.provider_key, iterations=req.iterations)]
    elif req.operation == "kem":
        result = benchmark_kem(req.provider_key, iterations=req.iterations)
        summaries = [result["encapsulate"], result["decapsulate"]]
    elif req.operation == "signature":
        result = benchmark_signature(req.provider_key, iterations=req.iterations)
        summaries = [result["sign"], result["verify"]]
    else:
        raise HTTPException(status_code=422, detail="operation must be one of: keygen, kem, signature")

    out = []
    for summary in summaries:
        benchmark = _get_or_create_benchmark(db, name=f"{req.provider_key}_{summary.operation}", operation=summary.operation, algorithm_id=spec.id)
        _persist_run(db, benchmark, summary)
        BENCHMARK_RUNS.labels(req.provider_key, summary.operation).inc()
        out.append(BenchmarkSummaryOut(**dataclasses.asdict(summary)))
    db.commit()
    record_audit(db, actor=user.username, action="run_benchmark", target_type="algorithm", target_id=spec.id,
                 after={"operation": req.operation, "iterations": req.iterations})
    return out


@router.get("/runs", response_model=list[BenchmarkSummaryOut])
def list_runs(provider_key: str | None = None, db: Session = Depends(get_db), _=Depends(require_viewer)):
    q = db.query(BenchmarkRun).join(Benchmark)
    if provider_key:
        try:
            spec = algo_registry.get_by_provider_key(provider_key)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        q = q.filter(Benchmark.algorithm_id == spec.id)
    runs = q.order_by(BenchmarkRun.created_at.desc()).limit(200).all()
    return [BenchmarkSummaryOut(**run.summary_stats_json) for run in runs]

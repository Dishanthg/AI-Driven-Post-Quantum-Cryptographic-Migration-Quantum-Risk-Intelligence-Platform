"""FastAPI application entrypoint (design doc Section 43).

Run: uvicorn app.main:app --reload --app-dir backend
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routers import (
    algorithms,
    assets,
    audit,
    auth,
    benchmarks,
    experiments,
    health,
    migrations,
    models,
    quantum,
    recommendations,
    risk,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import PrometheusMiddleware, metrics_response
from app.core.rate_limit import limiter

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-Driven Post-Quantum Cryptographic Migration & Quantum Risk Intelligence Platform",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware)

for router_module in (health, auth, assets, algorithms, risk, recommendations, migrations, benchmarks, quantum, models, experiments, audit):
    app.include_router(router_module.router)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()

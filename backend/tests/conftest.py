from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Must be set before any app.* module is imported (Settings is read once via
# an lru_cache'd get_settings()): a TestClient's requests all share one fake
# client host, so per-IP rate limiting meant for real traffic would otherwise
# make this suite itself flaky. See app/core/rate_limit.py.
os.environ.setdefault("QS_RATE_LIMIT_ENABLED", "false")

from app.crypto import registry as algo_registry
from app.db import models
from app.db.base import Base
from app.db.models import Algorithm


@pytest.fixture()
def db_session(tmp_path):
    """A fresh, isolated SQLite database per test, pre-seeded with the
    algorithm registry (reference data every other module depends on being
    present) but nothing else - each test scans/assesses/plans for itself."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    for spec in algo_registry.all_specs():
        session.add(Algorithm(
            id=spec.id, name=spec.name, family=spec.family, role=spec.role,
            classification=spec.classification, security_basis=spec.security_basis,
            quantum_vulnerability=spec.quantum_vulnerability, standard_ref=spec.standard_ref,
            library_source=spec.library_source, typical_key_size_bits=spec.typical_key_size_bits,
        ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def api_client(db_session):
    """A TestClient wired to the isolated `db_session` fixture instead of the
    application's real SQLite file, so API tests never touch dev/prod state."""
    from fastapi.testclient import TestClient

    from app.db.session import get_db as real_get_db
    from app.main import app

    def _override():
        yield db_session

    app.dependency_overrides[real_get_db] = _override
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def small_trained_model(tmp_path, monkeypatch):
    """Trains a small real risk model into an isolated artifact directory
    (never touching backend/artifacts/models) so ML-path tests are
    self-contained and reproducible without depending on a prior `make train`
    run having happened on this machine."""
    from app.core.config import get_settings

    monkeypatch.setenv("QS_MODEL_REGISTRY_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()

    from app.ai.train import train_and_evaluate
    out = train_and_evaluate(n_samples=400, seed=7)
    try:
        yield out
    finally:
        get_settings.cache_clear()

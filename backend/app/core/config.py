"""Central configuration. All experiment/runtime parameters are read from here or
YAML files under research/config/ - never hard-coded inline in business logic
(see project Rule: 'Do not hard-code experiment parameters')."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SECRET_KEY = "dev-only-change-me-via-QS_SECRET_KEY-env-var"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QS_", env_file=".env", extra="ignore")

    app_name: str = "QuantumShield"
    environment: str = "development"

    # Default to local SQLite for zero-friction dev/test; docker-compose brings up
    # real PostgreSQL for the "production-shaped" deployment (see infra/docker-compose.yml
    # and docs/architecture/adr/ADR-002-postgresql.md for the documented rationale/tradeoff).
    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'quantumshield.db'}"

    secret_key: str = DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    research_dir: Path = REPO_ROOT / "research"
    quantum_max_qubits: int = 16  # hard ceiling for Shor/Grover labs - see quantum/ module docstrings

    model_registry_dir: Path = REPO_ROOT / "backend" / "artifacts" / "models"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate limiting (design doc Section 50 - previously a documented gap, see
    # docs/security/threat-model.md). Disabled only for the pytest suite
    # (tests/conftest.py sets QS_RATE_LIMIT_ENABLED=false before importing
    # app.main) - a TestClient's requests all share one fake client host, so
    # per-IP throttling meant for real traffic would otherwise make the test
    # suite itself flaky rather than testing anything real.
    rate_limit_enabled: bool = True

    @model_validator(mode="after")
    def _reject_insecure_defaults_outside_development(self) -> Settings:
        """Fail fast rather than silently sign JWTs with a secret that is
        published in this repository's own source code. `development` (the
        pytest/local-dev default) is the only environment allowed to run
        without an explicit QS_SECRET_KEY - every other value (docker,
        staging, production, ...) must override it."""
        if self.environment != "development" and self.secret_key == DEFAULT_SECRET_KEY:
            raise RuntimeError(
                f"Refusing to start: QS_ENVIRONMENT={self.environment!r} but QS_SECRET_KEY is still the "
                "publicly-known development default. Set a real secret, e.g. "
                "QS_SECRET_KEY=$(python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

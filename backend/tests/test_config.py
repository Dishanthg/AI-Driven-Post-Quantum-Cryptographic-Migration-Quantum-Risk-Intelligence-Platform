"""Verifies the startup guard against running with the publicly-known
default JWT secret outside `development` - the fix for a real gap this
audit found: `docker-compose.yml`/README shipped a fallback secret key with
no code anywhere refusing to boot on it, so a `docker-compose up` without an
operator-set QS_SECRET_KEY would silently sign every JWT with a secret
visible in this repository's own source."""
from __future__ import annotations

import pytest

from app.core.config import DEFAULT_SECRET_KEY, Settings


def test_development_environment_allows_the_default_secret():
    settings = Settings(environment="development", secret_key=DEFAULT_SECRET_KEY, _env_file=None)
    assert settings.secret_key == DEFAULT_SECRET_KEY


def test_non_development_environment_rejects_the_default_secret():
    for env in ("docker", "staging", "production"):
        with pytest.raises(RuntimeError, match="Refusing to start"):
            Settings(environment=env, secret_key=DEFAULT_SECRET_KEY, _env_file=None)


def test_non_development_environment_accepts_an_overridden_secret():
    settings = Settings(environment="production", secret_key="a-real-generated-secret", _env_file=None)
    assert settings.secret_key == "a-real-generated-secret"

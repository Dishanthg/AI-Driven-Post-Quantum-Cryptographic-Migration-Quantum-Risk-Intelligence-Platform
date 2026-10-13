"""Verifies the rate-limiting mechanism actually throttles requests (design
doc Section 50), not just that it is wired into the app.

The real app disables rate limiting for the whole test session
(tests/conftest.py sets QS_RATE_LIMIT_ENABLED=false before app.main is
imported, since a TestClient's requests all share one fake client host).
This test therefore builds a small, separate FastAPI app using the exact
same slowapi Limiter class/decorator pattern as app/core/rate_limit.py and
app/api/routers/auth.py, but with limiting explicitly enabled, and fires
real HTTP requests through TestClient to confirm a 429 actually happens
once the configured limit is exceeded - a real, executed check of the
mechanism, not an assumption that the library works."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


def _build_rate_limited_app(limit: str) -> TestClient:
    limiter = Limiter(key_func=get_remote_address, enabled=True)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/limited")
    @limiter.limit(limit)
    def limited(request: Request):
        return {"ok": True}

    return TestClient(app)


def test_requests_within_the_limit_all_succeed():
    client = _build_rate_limited_app("5/minute")
    for _ in range(5):
        resp = client.get("/limited")
        assert resp.status_code == 200


def test_exceeding_the_limit_returns_429():
    client = _build_rate_limited_app("3/minute")
    statuses = [client.get("/limited").status_code for _ in range(5)]
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:], f"expected a 429 after exceeding the limit, got {statuses}"


def test_rate_limit_response_includes_retry_after_semantics():
    client = _build_rate_limited_app("1/minute")
    first = client.get("/limited")
    second = client.get("/limited")
    assert first.status_code == 200
    assert second.status_code == 429
    assert "rate limit" in second.json().get("error", second.text).lower()


def test_real_login_endpoint_does_not_500_with_rate_limiting_actually_enabled(db_session, api_client):
    """Regression test for a real bug this session caught: app/core/rate_limit.py
    sets headers_enabled=True, and slowapi's header-injection path requires the
    decorated endpoint to either return a starlette Response or declare a
    `response: Response` parameter FastAPI can inject headers into. Every
    dict-returning decorated route (login, run_benchmark, grover_run, shor_run)
    originally lacked that parameter, so the *synthetic* app above (which never
    sets headers_enabled) passed while the real app 500'd on every single
    successful request once rate limiting was actually turned on (slowapi only
    injects headers on the success path, not when a route raises) - exactly
    what the test suite disables globally (conftest.py), so nothing here would
    have noticed without a test that re-enables the app's real limiter and
    hits a real, successfully-completing route through it."""
    from app.core.rate_limit import limiter as app_limiter
    from app.core.security import ROLE_VIEWER, hash_password
    from app.db.models import User

    db_session.add(User(username="rl_probe", email="rl_probe@lab.local", hashed_password=hash_password("probe-password-123"), role=ROLE_VIEWER))
    db_session.commit()

    app_limiter.enabled = True
    try:
        r = api_client.post("/api/v1/auth/token", data={"username": "rl_probe", "password": "probe-password-123"})
    finally:
        app_limiter.enabled = False
    assert r.status_code == 200, r.text
    assert "X-RateLimit-Limit" in r.headers

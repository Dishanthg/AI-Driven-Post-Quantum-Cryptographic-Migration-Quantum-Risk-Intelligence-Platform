from __future__ import annotations

from app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, hash_password
from app.db.models import User


def _seed_user(db_session, username, role):
    password = f"{username}-password-123"
    db_session.add(User(username=username, email=f"{username}@lab.local", hashed_password=hash_password(password), role=role))
    db_session.commit()
    return password


def _login(api_client, username, password):
    r = api_client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_endpoint_ok(api_client):
    r = api_client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_unauthenticated_request_rejected(api_client):
    r = api_client.get("/api/v1/assets")
    assert r.status_code == 401


def test_login_rejects_bad_password(db_session, api_client):
    _seed_user(db_session, "someone", ROLE_VIEWER)
    r = api_client.post("/api/v1/auth/token", data={"username": "someone", "password": "wrong"})
    assert r.status_code == 401


def test_login_rejects_unknown_username_without_erroring(api_client):
    """A nonexistent username must still run the constant-time dummy-hash
    check (app/core/security.py::_DUMMY_PASSWORD_HASH) rather than short-
    circuit before touching bcrypt, so this must 401, not 500."""
    r = api_client.post("/api/v1/auth/token", data={"username": "nobody-such-user", "password": "whatever"})
    assert r.status_code == 401


def test_viewer_can_read_but_not_trigger_scan(db_session, api_client):
    password = _seed_user(db_session, "vwr", ROLE_VIEWER)
    headers = _login(api_client, "vwr", password)

    r = api_client.get("/api/v1/assets", headers=headers)
    assert r.status_code == 200

    r = api_client.post("/api/v1/assets/scan", headers=headers)
    assert r.status_code == 403


def test_analyst_can_run_full_pipeline_over_http(db_session, api_client):
    password = _seed_user(db_session, "anl", ROLE_ANALYST)
    headers = _login(api_client, "anl", password)

    r = api_client.post("/api/v1/assets/scan", headers=headers)
    assert r.status_code == 200
    assert r.json()["assets_created"] == 42

    r = api_client.get("/api/v1/assets/overview", headers=headers)
    assert r.status_code == 200
    assert r.json()["total_assets"] == 42

    r = api_client.post("/api/v1/risk/assess-all", json={"method": "rule_baseline"}, headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 42

    r = api_client.post("/api/v1/recommendations/recommend-all", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 42

    r = api_client.post("/api/v1/migrations/plan-all", headers=headers)
    assert r.status_code == 200
    plans = r.json()
    assert len(plans) > 0

    plan_id = plans[0]["id"]
    r = api_client.post(f"/api/v1/migrations/{plan_id}/simulate?iterations=3", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


def test_admin_only_audit_log(db_session, api_client):
    analyst_password = _seed_user(db_session, "anl2", ROLE_ANALYST)
    admin_password = _seed_user(db_session, "adm", ROLE_ADMIN)

    analyst_headers = _login(api_client, "anl2", analyst_password)
    api_client.post("/api/v1/assets/scan", headers=analyst_headers)  # generates an audit row

    r = api_client.get("/api/v1/audit", headers=analyst_headers)
    assert r.status_code == 403

    admin_headers = _login(api_client, "adm", admin_password)
    r = api_client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["action"] == "discovery_scan"


def test_quantum_grover_endpoint_enforces_qubit_cap(db_session, api_client):
    password = _seed_user(db_session, "anl3", ROLE_ANALYST)
    headers = _login(api_client, "anl3", password)
    r = api_client.post("/api/v1/quantum/grover/run", json={"n_qubits": 999, "marked_states": [0]}, headers=headers)
    assert r.status_code == 422


def test_shor_endpoint_returns_real_factors(db_session, api_client):
    password = _seed_user(db_session, "anl4", ROLE_ANALYST)
    headers = _login(api_client, "anl4", password)
    r = api_client.post("/api/v1/quantum/shor/run", json={"N": 15}, headers=headers)
    assert r.status_code == 200
    assert set(r.json()["factors"]) == {3, 5}

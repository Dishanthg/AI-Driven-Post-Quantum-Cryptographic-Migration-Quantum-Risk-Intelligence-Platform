from __future__ import annotations

from pathlib import Path

from app.db.models import Application, Asset
from app.discovery.scanner import scan_directory


def test_scan_imports_all_lab_configs(db_session):
    result = scan_directory(db_session)
    assert result.files_scanned == 8
    assert result.applications_seen == 8
    assert result.assets_created == 42
    assert result.errors == []
    assert db_session.query(Asset).count() == 42
    assert db_session.query(Application).count() == 8


def test_scan_is_idempotent(db_session):
    scan_directory(db_session)
    second = scan_directory(db_session)
    assert second.assets_created == 0
    assert second.assets_updated == 42
    assert db_session.query(Asset).count() == 42


def test_scan_reports_errors_without_aborting(db_session, tmp_path):
    good = tmp_path / "good.yaml"
    good.write_text(
        "application:\n  name: ok-app\n  business_unit: test\n  business_importance: low\n"
        "assets:\n  - hostname: ok-01\n    usage_type: tls_certificate\n    algorithm_id: ECDSA-P256\n"
        "    data_sensitivity: low\n    data_lifetime_years: 1\n    asset_criticality: low\n"
        "    internet_exposure: false\n    migration_complexity: low\n    current_status: legacy\n"
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "application:\n  name: bad-app\n  business_unit: test\n  business_importance: low\n"
        "assets:\n  - hostname: bad-01\n    usage_type: tls_certificate\n    algorithm_id: NOT-A-REAL-ALGORITHM\n"
        "    data_sensitivity: low\n    data_lifetime_years: 1\n    asset_criticality: low\n"
        "    internet_exposure: false\n    migration_complexity: low\n    current_status: legacy\n"
    )
    result = scan_directory(db_session, config_dir=tmp_path)
    assert result.assets_created == 1
    assert len(result.errors) == 1
    assert "bad.yaml" in result.errors[0]

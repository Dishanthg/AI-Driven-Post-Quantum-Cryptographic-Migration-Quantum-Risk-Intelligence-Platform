"""Cryptographic asset discovery (design doc Section 7/8).

Scans ONLY explicitly configured local lab targets: the YAML configuration
files under `enterprise_lab/configs/`. This module never reaches out over the
network and never scans arbitrary external systems - it is a config-file
importer, the same shape a real discovery agent would use against exported
TLS/application configuration, restricted here to a controlled lab (Rule in
design doc Section 7: "Do not scan arbitrary external systems").

Re-running a scan is idempotent: assets are matched by (application name,
hostname) and updated in place with a fresh `last_seen`, mirroring how a
periodic discovery scan would behave against a live fleet.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.crypto import registry as algo_registry
from app.db.models import Application, Asset, Certificate, CryptographicUsage

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "enterprise_lab" / "configs"


@dataclass
class ScanResult:
    source_dir: str
    files_scanned: int
    applications_seen: int
    assets_created: int
    assets_updated: int
    errors: list[str]


def _get_or_create_application(db: Session, app_cfg: dict) -> Application:
    existing = db.query(Application).filter_by(name=app_cfg["name"]).one_or_none()
    if existing:
        existing.business_unit = app_cfg.get("business_unit", existing.business_unit)
        existing.business_importance = app_cfg.get("business_importance", existing.business_importance)
        existing.description = app_cfg.get("description", existing.description)
        return existing
    application = Application(
        name=app_cfg["name"],
        business_unit=app_cfg.get("business_unit", "unknown"),
        business_importance=app_cfg.get("business_importance", "medium"),
        description=app_cfg.get("description", ""),
    )
    db.add(application)
    db.flush()
    return application


def _upsert_asset(db: Session, application: Application, asset_cfg: dict, source_file: str, now: dt.datetime) -> tuple[Asset, bool]:
    algorithm_id = asset_cfg["algorithm_id"]
    spec = algo_registry.get(algorithm_id)  # raises KeyError -> surfaced as a scan error if unknown algorithm

    existing = (
        db.query(Asset)
        .filter_by(application_id=application.id, hostname=asset_cfg["hostname"])
        .one_or_none()
    )
    key_size = asset_cfg.get("key_size_bits", spec.typical_key_size_bits)

    fields = dict(
        application_id=application.id,
        hostname=asset_cfg["hostname"],
        environment=asset_cfg.get("environment", "lab"),
        usage_type=asset_cfg["usage_type"],
        protocol=asset_cfg.get("protocol", ""),
        algorithm_id=algorithm_id,
        key_size_bits=key_size,
        data_sensitivity=asset_cfg.get("data_sensitivity", "medium"),
        data_lifetime_years=asset_cfg.get("data_lifetime_years", 1),
        asset_criticality=asset_cfg.get("asset_criticality", "medium"),
        internet_exposure=bool(asset_cfg.get("internet_exposure", False)),
        migration_complexity=asset_cfg.get("migration_complexity", "medium"),
        current_status=asset_cfg.get("current_status", "legacy"),
        discovery_source=f"config_scan:{source_file}",
        last_seen=now,
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        asset = existing
        created = False
    else:
        asset = Asset(**fields)
        db.add(asset)
        created = True
    db.flush()

    # cryptographic_usage: one row per discovered usage context (idempotent: clear+recreate for this asset)
    db.query(CryptographicUsage).filter_by(asset_id=asset.id).delete()
    db.add(CryptographicUsage(asset_id=asset.id, algorithm_id=algorithm_id, context=asset_cfg.get("protocol", asset_cfg["usage_type"])))

    cert_cfg = asset_cfg.get("certificate")
    if cert_cfg:
        db.query(Certificate).filter_by(asset_id=asset.id).delete()
        not_before = now
        not_after = now + dt.timedelta(days=365 * cert_cfg.get("validity_years", 1))
        db.add(Certificate(
            asset_id=asset.id,
            subject=cert_cfg["subject"],
            issuer=cert_cfg["issuer"],
            not_before=not_before,
            not_after=not_after,
            signature_algorithm_id=algorithm_id,
        ))

    return asset, created


def scan_directory(db: Session, config_dir: Path | None = None) -> ScanResult:
    config_dir = config_dir or DEFAULT_CONFIG_DIR
    now = dt.datetime.now(dt.UTC)
    files = sorted(config_dir.glob("*.yaml"))

    applications_seen = 0
    created, updated = 0, 0
    errors: list[str] = []

    for f in files:
        try:
            doc = yaml.safe_load(f.read_text())
            application = _get_or_create_application(db, doc["application"])
            applications_seen += 1
            for asset_cfg in doc.get("assets", []):
                try:
                    _asset, was_created = _upsert_asset(db, application, asset_cfg, f.name, now)
                    created += int(was_created)
                    updated += int(not was_created)
                except Exception as exc:
                    errors.append(f"{f.name}:{asset_cfg.get('hostname', '?')}: {exc}")
        except Exception as exc:
            errors.append(f"{f.name}: {exc}")

    db.commit()
    return ScanResult(
        source_dir=str(config_dir),
        files_scanned=len(files),
        applications_seen=applications_seen,
        assets_created=created,
        assets_updated=updated,
        errors=errors,
    )


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        result = scan_directory(session)
        print(f"Scanned {result.files_scanned} config files ({result.source_dir})")
        print(f"Applications seen: {result.applications_seen}")
        print(f"Assets created: {result.assets_created}, updated: {result.assets_updated}")
        if result.errors:
            print("Errors:")
            for e in result.errors:
                print(f"  - {e}")
    finally:
        session.close()

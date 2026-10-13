"""Pydantic response/request models for the API layer (design doc Section 43).

Read models mirror the DB schema closely (`from_attributes=True` reads
straight off the SQLAlchemy objects); write/action models are the minimal
input each endpoint actually needs. No endpoint accepts a client-supplied
risk score, benchmark value, or priority (Rule 8/9) - those are always
computed server-side.
"""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------- auth --
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(ORMModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool


# ---------------------------------------------------------------- inventory --
class AlgorithmOut(ORMModel):
    id: str
    name: str
    family: str
    role: str
    classification: str
    security_basis: str
    quantum_vulnerability: str
    standard_ref: str
    library_source: str
    typical_key_size_bits: int


class ApplicationOut(ORMModel):
    id: str
    name: str
    business_unit: str
    business_importance: str
    description: str


class CertificateOut(ORMModel):
    id: str
    subject: str
    issuer: str
    not_before: dt.datetime
    not_after: dt.datetime
    signature_algorithm_id: str


class AssetOut(ORMModel):
    id: str
    application_id: str
    hostname: str
    environment: str
    usage_type: str
    protocol: str
    algorithm_id: str
    key_size_bits: int
    data_sensitivity: str
    data_lifetime_years: int
    asset_criticality: str
    internet_exposure: bool
    migration_complexity: str
    current_status: str
    discovery_source: str
    last_seen: dt.datetime


class AssetDetailOut(AssetOut):
    application: ApplicationOut
    certificates: list[CertificateOut] = []


class ScanResultOut(BaseModel):
    source_dir: str
    files_scanned: int
    applications_seen: int
    assets_created: int
    assets_updated: int
    errors: list[str]


# -------------------------------------------------------------------- risk --
class RiskFactorOut(ORMModel):
    feature_name: str
    contribution: float


class RiskAssessmentOut(ORMModel):
    id: str
    asset_id: str
    method: str
    model_version_id: str | None
    risk_score: float
    priority: str
    confidence: float
    created_at: dt.datetime
    factors: list[RiskFactorOut] = []


class RiskAssessRequest(BaseModel):
    method: str = "ml_model"  # "ml_model" | "rule_baseline"


# ----------------------------------------------------------------- pqc rec --
class PQCRecommendationOut(ORMModel):
    id: str
    asset_id: str
    risk_assessment_id: str
    strategy: str
    target_algorithm_id: str | None
    rationale: str
    assumptions: str
    tradeoffs: str


# --------------------------------------------------------------- migration --
class MigrationStepOut(ORMModel):
    id: str
    sequence: int
    stage: str
    description: str
    status: str
    simulated_result_json: dict


class MigrationPlanOut(ORMModel):
    id: str
    asset_id: str
    recommendation_id: str
    current_algorithm_id: str
    target_algorithm_id: str
    priority: str
    estimated_effort_hours: float
    performance_impact_json: dict
    compatibility_risk: str
    rollback_strategy: str
    verification_criteria: str
    owner: str
    status: str
    steps: list[MigrationStepOut] = []


# --------------------------------------------------------------- benchmark --
class BenchmarkRunRequest(BaseModel):
    provider_key: str
    operation: str  # "keygen" | "kem" | "signature"
    iterations: int = 50


class BenchmarkSummaryOut(BaseModel):
    operation: str
    provider_key: str
    iterations: int
    mean_ms: float
    median_ms: float
    stdev_ms: float
    p95_ms: float
    p99_ms: float
    ci95_low_ms: float
    ci95_high_ms: float
    public_key_bytes: int | None
    ciphertext_or_signature_bytes: int | None
    environment: dict


# ----------------------------------------------------------------- quantum --
class GroverRunRequest(BaseModel):
    n_qubits: int = 4
    marked_states: list[int] = [5]
    shots: int = 2048
    seed: int = 42


class ShorRunRequest(BaseModel):
    N: int = 15
    a: int | None = None
    counting_qubits: int = 8
    shots: int = 2048
    seed: int = 42


class ThreatEntryOut(BaseModel):
    algorithm_family: str
    attack_model: str
    classical_security_assumption: str
    theoretical_quantum_complexity: str
    practical_constraint: str
    current_limitation: str
    plain_language_explanation: str


# ----------------------------------------------------------------- mlops ---
class ModelVersionOut(ORMModel):
    id: str
    version: str
    algorithm: str
    dataset_ref: str
    random_seed: int
    metrics_json: dict
    artifact_path: str
    is_active: bool


# ----------------------------------------------------------------- audit ---
class AuditLogOut(ORMModel):
    id: str
    timestamp: dt.datetime
    actor: str
    action: str
    target_type: str
    target_id: str
    before_json: dict
    after_json: dict


# ---------------------------------------------------------------- overview --
class InventoryOverviewOut(BaseModel):
    total_assets: int
    legacy_public_key_assets: int
    high_risk_assets: int
    critical_risk_assets: int
    pqc_migrated_assets: int
    hybrid_assets: int
    algorithm_distribution: dict[str, int]
    priority_distribution: dict[str, int]
    migration_status_distribution: dict[str, int]

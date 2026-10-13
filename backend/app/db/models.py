"""SQLAlchemy models for every entity in the design doc (Section 42).

Every "run" table (BenchmarkRun, QuantumRun, ExperimentRun) shares a provenance
shape - config, seed, environment, raw + summary results, timestamps - so that
every number surfaced anywhere in the system is traceable back to an executed
run. Nothing here stores a literal risk score or benchmark value as a constant.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# ---------------------------------------------------------------- identity --
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# --------------------------------------------------------------- inventory --
class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    business_unit: Mapped[str] = mapped_column(String(128), default="unknown")
    business_importance: Mapped[str] = mapped_column(String(16), default="medium")  # low/medium/high/critical
    description: Mapped[str] = mapped_column(Text, default="")

    assets: Mapped[list[Asset]] = relationship(back_populates="application")


class Algorithm(Base, TimestampMixin):
    __tablename__ = "algorithms"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "RSA-2048", "ML-KEM-768"
    name: Mapped[str] = mapped_column(String(64))
    family: Mapped[str] = mapped_column(String(32))  # RSA, ECC, AES, SHA2, ML-KEM, ML-DSA, SLH-DSA, HYBRID
    role: Mapped[str] = mapped_column(String(32))  # public_key, key_exchange, signature, symmetric, hash
    classification: Mapped[str] = mapped_column(String(32))  # classical_pk / classical_sym / hash / pqc_kem / pqc_sig / hybrid
    security_basis: Mapped[str] = mapped_column(String(64))  # factoring / discrete_log / lattice / hash / code
    quantum_vulnerability: Mapped[str] = mapped_column(String(32))  # quantum_vulnerable / quantum_weakened / not_significantly_affected
    standard_ref: Mapped[str] = mapped_column(String(64), default="")
    library_source: Mapped[str] = mapped_column(String(64), default="")
    typical_key_size_bits: Mapped[int] = mapped_column(Integer, default=0)


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    subject: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str] = mapped_column(String(255))
    not_before: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    signature_algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))

    asset: Mapped[Asset] = relationship(back_populates="certificates")


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id"))
    hostname: Mapped[str] = mapped_column(String(128))
    environment: Mapped[str] = mapped_column(String(32), default="lab")  # lab/dev/staging/prod(simulated)
    usage_type: Mapped[str] = mapped_column(String(64))  # tls_certificate, key_exchange, signing, data_at_rest, ...
    protocol: Mapped[str] = mapped_column(String(128), default="")
    algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))
    key_size_bits: Mapped[int] = mapped_column(Integer, default=0)
    data_sensitivity: Mapped[str] = mapped_column(String(16), default="medium")  # low/medium/high/critical
    data_lifetime_years: Mapped[int] = mapped_column(Integer, default=1)
    asset_criticality: Mapped[str] = mapped_column(String(16), default="medium")
    internet_exposure: Mapped[bool] = mapped_column(Boolean, default=False)
    migration_complexity: Mapped[str] = mapped_column(String(16), default="medium")
    current_status: Mapped[str] = mapped_column(String(32), default="legacy")  # legacy/hybrid/pqc_migrated
    discovery_source: Mapped[str] = mapped_column(String(64), default="config_scan")
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    application: Mapped[Application] = relationship(back_populates="assets")
    certificates: Mapped[list[Certificate]] = relationship(back_populates="asset")
    usages: Mapped[list[CryptographicUsage]] = relationship(back_populates="asset")
    risk_assessments: Mapped[list[RiskAssessment]] = relationship(back_populates="asset")


class CryptographicUsage(Base, TimestampMixin):
    __tablename__ = "cryptographic_usage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))
    context: Mapped[str] = mapped_column(String(64))  # e.g. "TLS 1.3 key exchange", "JWT signing"

    asset: Mapped[Asset] = relationship(back_populates="usages")


# -------------------------------------------------------------------- risk --
class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    method: Mapped[str] = mapped_column(String(32))  # "rule_baseline" or "ml_model"
    model_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("model_versions.id"), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(16))  # critical/high/medium/low
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)

    asset: Mapped[Asset] = relationship(back_populates="risk_assessments")
    factors: Mapped[list[RiskFactor]] = relationship(back_populates="assessment")


class RiskFactor(Base, TimestampMixin):
    __tablename__ = "risk_factors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("risk_assessments.id"))
    feature_name: Mapped[str] = mapped_column(String(64))
    contribution: Mapped[float] = mapped_column(Float)  # SHAP value or rule weight contribution

    assessment: Mapped[RiskAssessment] = relationship(back_populates="factors")


# ---------------------------------------------------------------- migration --
class PQCRecommendation(Base, TimestampMixin):
    __tablename__ = "pqc_recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    risk_assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("risk_assessments.id"))
    strategy: Mapped[str] = mapped_column(String(32))  # pqc_migration/hybrid_migration/deferred/agility_prep/manual_review
    target_algorithm_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("algorithms.id"), nullable=True)
    rationale: Mapped[str] = mapped_column(Text)
    assumptions: Mapped[str] = mapped_column(Text, default="")
    tradeoffs: Mapped[str] = mapped_column(Text, default="")


class MigrationPlan(Base, TimestampMixin):
    __tablename__ = "migration_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("pqc_recommendations.id"))
    current_algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))
    target_algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))
    priority: Mapped[str] = mapped_column(String(16))
    estimated_effort_hours: Mapped[float] = mapped_column(Float, default=0.0)
    performance_impact_json: Mapped[dict] = mapped_column(JSON, default=dict)
    compatibility_risk: Mapped[str] = mapped_column(String(16), default="medium")
    rollback_strategy: Mapped[str] = mapped_column(Text, default="")
    verification_criteria: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(64), default="unassigned")
    status: Mapped[str] = mapped_column(String(32), default="proposed")  # proposed/approved/in_progress/completed/rolled_back

    steps: Mapped[list[MigrationStep]] = relationship(back_populates="plan")


class MigrationStep(Base, TimestampMixin):
    __tablename__ = "migration_steps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("migration_plans.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(32))  # legacy/hybrid/pqc_enabled
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    simulated_result_json: Mapped[dict] = mapped_column(JSON, default=dict)

    plan: Mapped[MigrationPlan] = relationship(back_populates="steps")


# --------------------------------------------------------------- benchmark --
class Benchmark(Base, TimestampMixin):
    __tablename__ = "benchmarks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(32))  # keygen/encapsulate/decapsulate/sign/verify
    algorithm_id: Mapped[str] = mapped_column(String(64), ForeignKey("algorithms.id"))

    runs: Mapped[list[BenchmarkRun]] = relationship(back_populates="benchmark")


class BenchmarkRun(Base, TimestampMixin):
    __tablename__ = "benchmark_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    benchmark_id: Mapped[str] = mapped_column(String(36), ForeignKey("benchmarks.id"))
    iterations: Mapped[int] = mapped_column(Integer)
    environment_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    raw_results_json: Mapped[dict] = mapped_column(JSON, default=dict)  # {"timings_ms": [...]}
    summary_stats_json: Mapped[dict] = mapped_column(JSON, default=dict)

    benchmark: Mapped[Benchmark] = relationship(back_populates="runs")


# ----------------------------------------------------------------- quantum --
class QuantumExperiment(Base, TimestampMixin):
    __tablename__ = "quantum_experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))  # shor/grover
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)

    runs: Mapped[list[QuantumRun]] = relationship(back_populates="experiment")


class QuantumRun(Base, TimestampMixin):
    __tablename__ = "quantum_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("quantum_experiments.id"))
    backend: Mapped[str] = mapped_column(String(32), default="aer_simulator")
    noise_model: Mapped[str] = mapped_column(String(32), default="ideal")
    qubits: Mapped[int] = mapped_column(Integer)
    circuit_depth: Mapped[int] = mapped_column(Integer)
    shots: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runtime_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    success_probability: Mapped[float] = mapped_column(Float, default=0.0)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_real_hardware: Mapped[bool] = mapped_column(Boolean, default=False)

    experiment: Mapped[QuantumExperiment] = relationship(back_populates="runs")


# ----------------------------------------------------------------- audit ---
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(64))
    before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    after_json: Mapped[dict] = mapped_column(JSON, default=dict)


# ----------------------------------------------------------------- mlops ---
class MLModel(Base, TimestampMixin):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True)  # e.g. "risk_prioritization"

    versions: Mapped[list[ModelVersion]] = relationship(back_populates="model")


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"))
    version: Mapped[str] = mapped_column(String(32))
    algorithm: Mapped[str] = mapped_column(String(32))  # logistic_regression/random_forest/xgboost
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)
    hyperparameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    dataset_ref: Mapped[str] = mapped_column(String(128))
    random_seed: Mapped[int] = mapped_column(Integer)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_path: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    model: Mapped[MLModel] = relationship(back_populates="versions")


# ------------------------------------------------------------- experiments --
class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(64), unique=True)  # human key e.g. "exp1_pqc_performance"
    hypothesis: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")

    runs: Mapped[list[ExperimentRun]] = relationship(back_populates="experiment")


class ExperimentRun(Base, TimestampMixin):
    __tablename__ = "experiment_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiments.id"))
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    environment_json: Mapped[dict] = mapped_column(JSON, default=dict)
    git_commit: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    results_json: Mapped[dict] = mapped_column(JSON, default=dict)

    experiment: Mapped[Experiment] = relationship(back_populates="runs")

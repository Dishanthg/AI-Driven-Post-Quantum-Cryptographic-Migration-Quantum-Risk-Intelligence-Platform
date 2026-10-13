# ADR-002: PostgreSQL as the production-shaped database, SQLite for local dev/test

## Status
Accepted, implemented (`backend/app/core/config.py`, `backend/alembic/`,
`docker-compose.yml`).

## Context
The design (Section 42) specifies a relational schema with ~20 entities
(users, assets, algorithms, certificates, risk_assessments, risk_factors,
pqc_recommendations, migration_plans/steps, benchmarks/benchmark_runs,
quantum_experiments/runs, audit_logs, models/model_versions,
experiments/experiment_runs) with meaningful foreign-key relationships (an
asset has many risk assessments over time; a migration plan has many ordered
steps; a benchmark has many runs). This is a relational workload, not a
document or key-value one.

## Problem
Which database, and how do we keep local iteration fast without diverging
from a realistic deployment shape?

## Alternatives considered
- **SQLite only.** Rejected as the sole target — no native JSONB, weaker
  concurrent-write story, and it would understate the "production-grade"
  claim in the project brief.
- **PostgreSQL only, including local dev.** Rejected as the only option —
  adds a Docker/service dependency to the inner dev loop (running a single
  test or the demo script) for no benefit during early iteration.
- **PostgreSQL for structured data + a separate document store for
  raw_results_json/environment_json blobs.** Rejected — unnecessary
  complexity; Postgres's native JSONB column type already covers these
  fields (benchmark raw results, quantum run parameters, audit before/after
  snapshots) without a second system.

## Decision
Use SQLAlchemy against both backends through the same models
(`backend/app/db/models.py`) and Alembic migrations:
- **Local dev/test default:** SQLite file (`backend/quantumshield.db`),
  zero-friction, no external service required to run `pytest` or `make demo`.
- **`docker-compose.yml` / "production-shaped" deployment:** PostgreSQL 16,
  connected via `QS_DATABASE_URL=postgresql+psycopg://...`.

The switch is a single environment variable
(`app.core.config.Settings.database_url`), not a code change — consistent
with the project's broader agility philosophy (ADR-001).

## Consequences
- Positive: contributors can run the full test suite and demo with no
  external services.
- Positive: `docker-compose.yml` demonstrates the intended production
  topology (Postgres + backend + frontend + Prometheus + Grafana) end to end.
- Negative / known gap, now partially closed: SQLite and PostgreSQL are not
  behaviorally identical. This was not just a theoretical concern - running
  the real end-to-end demo pipeline against a real `docker-compose`
  PostgreSQL instance (Alembic migrations + `scripts.run_demo`) caught a
  genuine bug: `assets.protocol` was `VARCHAR(32)`, but SQLite does not
  enforce VARCHAR length limits at all, so a real 50-character config value
  had been silently accepted throughout earlier development under SQLite
  and was only (correctly) rejected by PostgreSQL's
  `StringDataRightTruncation`. Fixed via a proper Alembic migration
  (`4a66b1719aaf`) widening the column to `VARCHAR(128)`. A dedicated
  `postgres-integration` CI job (real Postgres service container,
  migrations + full demo pipeline) now runs this automatically. What
  remains open: the pytest suite's own test *assertions*
  (`tests/conftest.py`) still run against a hard-coded SQLite fixture, not
  Postgres - only the demo pipeline has been verified against the real
  target, not every unit test. See `research/RESEARCH_LOG.md` and
  `docs/masters-application/13_failures_and_lessons.md` for the full story.

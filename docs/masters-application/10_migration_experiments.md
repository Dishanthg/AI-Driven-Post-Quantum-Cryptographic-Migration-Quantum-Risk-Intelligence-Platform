# 10. Migration Experiments

Real, re-executed pipeline run against the 42-asset synthetic enterprise lab
(this session, `python -m app.discovery.scanner` →
`app.risk.service` → `app.recommendations.engine` → `app.migration.planner`):

- **Discovery:** 8 config files scanned, 42 assets present (0 newly created
  this run since the lab was already seeded, 42 updated).
- **Risk assessment:** priority distribution — critical: 9, high: 10,
  medium: 19, low: 4.
- **Recommendations:** strategy distribution — `hybrid_migration`: 7,
  `pqc_migration`: 9, `deferred`: 7, `agility_prep`: 14, `manual_review`: 5.
  (14 + 9 + 7 assets have no scheduled plan output — `deferred` and
  `agility_prep`/`manual_review` don't produce a MigrationPlan by design,
  see `app/migration/planner.py`'s module docstring.)
- **Migration planning:** 32 migration plans generated (`pqc_migration` +
  `hybrid_migration` recommendations only), **1183.0 total estimated
  hours** across all 32 plans.

## Effort estimation formula (deterministic, not ML — see `ADR-003`)
```
hours = BASE_HOURS[migration_complexity] * CRITICALITY_MULTIPLIER[asset_criticality]
        + INTERNET_EXPOSURE_EXTRA_HOURS (if internet-facing)
        + HYBRID_EXTRA_HOURS (if strategy == hybrid_migration)
```
Every plan's `estimated_effort_hours` ships with the exact formula string
used to compute it (`EffortEstimate.formula`), so any number in the UI or
API is independently checkable, not opaque.

## Migration simulator
Each plan's stages are simulated by actually invoking the relevant
`CryptoProvider` operations and real benchmarks for the stage's algorithm
(`app/migration/simulator.py`), plus an explicit roundtrip correctness
check (encapsulate/decapsulate or sign/verify) per stage — never an
estimated or hard-coded performance number for a simulated stage. For
`hybrid_migration` plans, the eventual full-PQC stage is explicitly
described as "future, not scheduled by this plan," not silently simulated
as already complete.

## What this experiment does and does not establish
It establishes that the recommendation → plan → simulate pipeline runs
end-to-end on real (if synthetic) inventory data and produces internally
consistent, re-derivable numbers. It does **not** establish that 1183 hours
is an accurate estimate of what a real migration of this scope would take —
there is no real-world migration-hours ground truth to calibrate against
(Section 60's explicit, acknowledged limitation, also noted in
`app/migration/planner.py`'s own docstring). The formula's coefficients
(`BASE_HOURS`, `CRITICALITY_MULTIPLIER`, etc.) are engineering judgment
calls, documented as such, not fitted to data.

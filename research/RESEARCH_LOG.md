# Research Log

Chronological record of what was actually built, run, and observed — including
failures — per the master build prompt's Rule 15 (label everything NOT
IMPLEMENTED / IMPLEMENTED — NOT VERIFIED / VERIFIED) and Section 61 ("do not
hide failed experiments"). Timestamps are taken from git commit history and
model-artifact directory names, not reconstructed from memory.

Honesty note on cadence: this project was built across one extended,
multi-session engineering effort rather than a slow multi-week research
cadence — the git history below (all commits on 2026-09-04, with model
artifacts from 2026-09-03/04) reflects that directly. This log records what
was actually done, not a fabricated slower timeline.

---

## 2026-09-03 21:35 UTC — First AI risk model training run
**Experiment:** Experiment 3 (AI Risk Prioritization), initial pass.
**Configuration:** `app.ai.train.train_and_evaluate(n_samples=2000, seed=42)`.
**Result:** VERIFIED. Artifact persisted at
`backend/artifacts/models/risk_prioritization/20260903T213526Z/`.
**Next step:** review whether the ranking-consistency (Kendall's τ) metric
for H1 needed a dedicated cross-fold analysis rather than a single split.

## 2026-09-04 05:53 UTC — Retrained model with ranking-consistency (H1) metric added
**Research question:** H1 — does AI-assisted prioritization give more
consistent rankings than a static rule?
**Configuration:** same dataset generator/seed; added 5-fold RandomForest
retraining to compute pairwise Kendall's τ across folds vs. the rule
baseline's (deterministic, hence τ=1.0 by construction) self-consistency.
**Result:** VERIFIED, real numbers, not fabricated:
- macro-F1: rule_baseline 0.7232, logistic_regression 0.7897,
  random_forest 0.7709, xgboost 0.7349 (n_test=600).
- ranking consistency: ML fold-pairwise τ mean 0.9317 (min 0.9267); rule
  baseline self-consistency τ=1.0 (deterministic, not a meaningful
  comparison point on its own); ML-vs-rule agreement τ=0.8170.
**Interpretation:** logistic regression outperformed both RandomForest and
XGBoost on this synthetic, noisy, nonlinear-interaction dataset — notably,
*not* the more complex models. XGBoost did **not** beat the rule baseline by
a wide margin (0.7349 vs. 0.7232) despite being the most complex model
tried; this is reported as-is rather than adjusted, per Rule 20 ("do not
automatically assume XGBoost is superior"). See ADR-003 and
`research/tables/risk_model_comparison.md`.
**Failure/surprise worth recording:** the initial expectation going in was
that XGBoost would clearly outperform both the rule baseline and logistic
regression; it did not. This is treated as a genuine finding (the synthetic
label's interaction term may be simple enough that a linear model with the
right features already captures most of the signal, and gradient boosting's
extra flexibility here mostly overfits on n=1400 training rows) rather than
a bug to "fix" by retuning until XGBoost wins.
**Artifact:** `backend/artifacts/models/risk_prioritization/20260904T055302Z/metadata.json`.

## 2026-09-04 11:22 UTC — Initial checkpoint committed (`6ad371c`)
Crypto algorithm registry, CryptoProvider abstraction (Classical/PQC/Hybrid),
quantum threat model, Grover/Shor labs, AI risk engine (dataset generator,
rule baseline, LogReg/RF/XGBoost training, SHAP explainability) reach a first
working state.
**Verification at this point:** manual roundtrip checks during development
(RSA, ECDSA, ECDH, ML-KEM-512/768/1024, ML-DSA-44/65, SLH-DSA-SHA2-128f, and
the ECDH+ML-KEM hybrid composition) — not yet backed by an automated test
suite (that came later, see 2026-09-04 18:09 entry).

## 2026-09-04 11:33 UTC — Inventory/discovery/migration pipeline (`2ca5149`)
Alembic migrations for the full ~20-entity schema, `enterprise_lab/` sample
enterprise (8 services with distinct cryptographic configs), discovery
scanner, risk service, recommendation engine, migration planner and
simulator land.

## 2026-09-04 11:44 UTC — FastAPI layer + crypto-agility demo (`5573e42`)
11 versioned API routers, JWT auth + RBAC (viewer/analyst/admin), audit
logging, and the standalone crypto-agility demo
(`backend/agility_demo/secure_api.py` vs.
`backend/agility_demo/tightly_coupled_baseline.py`, for Experiment 6) land.

## 2026-09-04 18:09 UTC — Observability, automated tests, Docker/Compose (`bedd1d9`)
**What changed:** Prometheus metrics middleware, a 66-case pytest suite
covering crypto providers, quantum labs, the AI risk engine (including a
real end-to-end SHAP explanation call), the benchmark engine, discovery
scanner, migration pipeline, crypto-agility demo, the API layer, the
algorithm registry, and a dedicated `test_research_integrity.py` module that
asserts quantum lab results are always labeled and that the Shor lab never
claims to have broken RSA.
**Result:** VERIFIED — `66 passed, 0 failed` (re-run and confirmed live
during this session; see FINAL_RESEARCH_AUDIT.md for the exact command and
timing).
**Also this session:** `research/generate_report_assets.py` was written to
turn already-executed artifacts (`research/tables/benchmark_sweep.csv` from
`make benchmark`; the latest risk-model `metadata.json` from `make train`)
into figures/tables, deliberately with no simulation or synthetic-value
generation of its own — if a prerequisite artifact is missing, the
corresponding output is skipped and reported as NOT GENERATED rather than
invented. Ruff lint was added and the full `app/` tree brought to a clean
`ruff check` pass (93 → 0 findings; see git history for the specific
fixes — mostly import ordering, one `zip(..., strict=True)`, three
ambiguous single-letter variable names, and one genuinely unused unpacked
variable). ADR-001 through ADR-007 were written, each grounded in and
cross-referenced against the actual module docstrings that had already
described these decisions in the code.

## 2026-09-04 (later same session) — Experiment 6 (crypto agility) and ablation study executed
**Gap found:** `backend/agility_demo/README.md` already referenced
`research/experiments/exp6_crypto_agility.py` and
`research/tables/exp6_crypto_agility.md` as if they existed; neither did.
Built and ran both this session rather than leaving the reference dangling.
**Experiment 6 result (VERIFIED, real execution):** swapping
`backend/agility_demo/secure_api.py` through
ECDSA-P256 -> ML-DSA-65 -> SLH-DSA-SHA2-128F via `set_active_provider`
produced **0 changed lines** in the business-logic file at every step
(verified by SHA-256 hash equality, not asserted), with a real sign/verify
roundtrip succeeding at each step (signature sizes 71 / 3309 / 17088 bytes —
consistent with the independently-measured `research/tables/benchmark_sweep.csv`
values for the same algorithms, which is a useful cross-check). The
tightly-coupled comparison file has 4 statically-documented hard-wired
call sites that a real migration would have to touch. See
`research/tables/exp6_crypto_agility.md`/`.json`.
**Ablation study (Section 40) result (VERIFIED, real execution):**
`research/experiments/ablation_risk_features.py` retrains
LogisticRegression with one feature dropped at a time. Findings, most to
least damaging: removing `internet_exposure_bin` costs the most
(macro-F1 0.7897 -> 0.4479, Δ=-0.3417) — expected, since it participates in
both the linear term and the withheld nonlinear interaction term in the
synthetic label. `quantum_vulnerability_ord` (Δ=-0.2472) and
`data_sensitivity_ord` (Δ=-0.1413) are next most important, again matching
their label-formula weights. **Notable, unplanned finding:** removing
`key_size_norm` (Δ=+0.0102) or `migration_complexity_ord` (Δ=+0.0162)
*improved* macro-F1 slightly. Checking `app/ai/dataset.py::true_risk_score`
confirms why: `migration_complexity` is generated as a feature but is **not**
used anywhere in the synthetic label formula — it is pure noise from the
model's perspective, so dropping it acts as a mild regularizer. This was not
anticipated going in; it is reported as found rather than treated as a
result to explain away, and it is a legitimate caution for interpreting the
ablation table (a feature's presence in the schema does not imply it is
causally relevant to the label it's being evaluated against). See
`research/tables/ablation_risk_features.md`.

---

## 2026-09-04 (later same session) — Experiment 8: noise analysis executed
**What changed:** `run_grover` gained an optional `noise_model` parameter
(default `None`, so all existing callers/tests are unaffected — verified by
re-running the full suite after the change). Built
`research/experiments/exp8_noise_analysis.py`, which runs the same
4-qubit/marked-state-5 Grover search under an ideal `AerSimulator` and under
a depolarizing (0.1% 1-qubit gates, 1% CX) + readout-error (2%) noise
model. These rates are explicitly labeled as illustrative/NISQ-like, **not**
fitted to any specific real device.
**Result (VERIFIED, real execution, n=4096 shots each):** ideal success
probability 0.9614 (circuit depth 14) vs. noisy success probability 0.4387
(circuit depth 171 after transpilation to a noise-eligible basis gate set) —
a genuine, substantial success-probability collapse under even modest
per-gate error rates, consistent with the well-known fragility of
multi-round amplitude amplification to gate noise (Grover's diffuser/oracle
repeat `optimal_iterations` times, compounding per-gate error). Real quantum
hardware was **NOT RUN** — no hardware backend credentials or integration
exist in this repository; this is reported explicitly per Section 39 rather
than omitted. See `research/tables/exp8_noise_analysis.md`/`.json`.

---

## 2026-09-04 (continuation session) — Closed the remaining gaps: benchmark-aware recommendations, all 4 Section-40 ablations, significance testing, PostgreSQL verification, real screenshots

**Wired real benchmark data into the recommendation engine (closes a real
Section 24 gap).** `app/recommendations/engine.py` never consulted
benchmark data at all before this session, which made "PQC benchmark
information" ablation impossible to test meaningfully. Added
`_real_benchmarked_signature_bytes()`: for long-lived (>10y), internet-
facing, TLS-certificate-usage signature assets, if a real completed
benchmark run shows the conservative SLH-DSA-SHA2-128F choice's signature
size exceeds an 8000-byte TLS-handshake-fragmentation budget (a real,
documented PQC-TLS deployment concern), the recommender now switches to
ML-DSA-65 instead and says exactly why, citing the real measured byte
count. Verified with two new tests
(`test_recommendation_falls_back_to_hash_based_signature_without_benchmark_data`,
`test_recommendation_uses_real_benchmark_data_to_avoid_tls_handshake_bloat`)
- suite now 68/68.

**Built and ran the remaining 3 of Section 40's 4 ablation types**
(previously only feature ablation existed):
- `ablation_benchmark_info.py`: runs the real pipeline with vs. without
  benchmark data available. Result: **0 of 42 assets changed** - verified
  this is a real finding (no asset in the current lab config meets the
  long-lived+internet-facing+TLS-certificate+classical-signature
  combination the new logic checks for), not a bug, by directly checking
  the lab YAML configs.
- `ablation_ai_model.py`: runs the real pipeline with the ML model vs. the
  rule baseline feeding risk assessment. Result: **3 of 42 assets (7.1%)**
  get a different PQC recommendation strategy, and 2 migration plans get a
  different priority, depending on which risk-assessment method is used -
  a genuine, non-trivial downstream consequence of the model-vs-rule choice.
- `ablation_explainability.py`: compares real per-feature attribution
  (exact logistic-regression coefficients, matching what `app/ai/explain.py`
  computes) against a cheap, model-free heuristic (rank by |standardized
  value|). Result: mean top-3 Jaccard overlap only 0.425, exact-match rate
  10.5%, full-ranking Spearman correlation only 0.104 - the real
  attribution method disagrees substantially with the naive heuristic most
  of the time, supporting its use.

**BUG FOUND AND FIXED (twice, same root cause) during ablation development:**
`ablation_ai_model.py`'s first version joined the two pipeline runs'
results by `Asset.id` - but each run uses a *fresh* temporary database, and
`Asset.id` is a randomly-generated UUID assigned at insert time, so it is
never the same value across two separate runs. The join silently matched
nothing, producing a false "0 recommendations changed, 0 priorities
changed" result that looked like a clean null finding but was actually a
broken comparison. Caught by noticing an inconsistency (0 detected changes,
but a *different* migration-plan count between the two runs, which is
contradictory if truly nothing changed) rather than accepting the
first number at face value. Fixed by joining on `hostname` (deterministic,
sourced from the lab config files) instead, with an assertion that the two
runs' hostname sets match before comparing. **The exact same bug was then
found pre-emptively in `ablation_benchmark_info.py`** (written with the
same asset_id-join pattern) and fixed the same way before it was ever
reported as a result - its 0-changed result above was re-verified as
genuine only after this fix, by directly checking the lab YAML data for
the condition the new recommendation logic looks for.

**Statistical significance testing (Section 41, previously NOT IMPLEMENTED).**
`significance_testing.py` runs a real retraining (same seed/hyperparameters
as `app/ai/train.py`) and computes paired bootstrap 95% CIs (n=2000
resamples) and paired permutation tests (n=2000) on macro-F1 differences
between every pair of models. Results, real and somewhat surprising:
- logistic regression vs. rule baseline: **significant** (95% CI
  [+0.033, +0.101], permutation p=0.0005)
- logistic regression vs. XGBoost: **significant** (95% CI
  [+0.013, +0.096], permutation p=0.010)
- logistic regression vs. random forest: NOT significant (CI includes 0,
  p=0.347)
- **XGBoost vs. rule baseline: NOT significant** (CI includes 0,
  p=0.659) - this substantially strengthens the earlier point-estimate
  observation ("XGBoost barely beat the rule baseline") into a rigorous
  claim: XGBoost's apparent edge over the deterministic rule baseline is
  statistically indistinguishable from resampling noise on this dataset.
- random forest vs. rule baseline: borderline, not significant at 95%
  (p=0.056, CI upper bound near zero)

**PostgreSQL deployment path verified for real (closes ADR-002's stated
gap).** Started the real `docker-compose.yml` postgres service (Docker
Desktop needed to be started first - it was not running), applied Alembic
migrations against it, and ran the full `scripts.run_demo --retrain`
pipeline against real PostgreSQL. **This caught a real bug**: `assets.protocol`
was `VARCHAR(32)`, but real lab config values (e.g. "firmware image signing
(long-lived trust anchor)", 50 chars) exceed that - SQLite silently
tolerates oversized VARCHAR values (no enforcement), PostgreSQL correctly
rejected the insert with `StringDataRightTruncation`. This is precisely
the kind of SQLite/PostgreSQL behavioral divergence ADR-002 flagged as
"not independently re-audited." Fixed by widening the column to
VARCHAR(128) (checked against the longest real value across all 8 configs
plus the generated internal-mesh, max 48 chars, so 128 leaves real
headroom) via a proper Alembic migration
(`4a66b1719aaf_widen_asset_protocol_column_to_128_chars.py`), generated
with `alembic revision --autogenerate` against the live Postgres instance.
Re-ran the full demo pipeline against Postgres after the fix: clean,
identical priority distribution and macro-F1 values to the SQLite run
(9/10/19/4 critical/high/medium/low; macro-F1 0.7897/0.7709/0.7349/0.7232
for LogReg/RF/XGBoost/rule). Also added a dedicated `postgres-integration`
CI job (real Postgres service container, migrations + full demo pipeline)
so this verification is now durable/automated, not a one-off manual check.

**Disk-space incident during this work:** building the `docker-compose`
backend/frontend images filled the machine's `C:` drive to 0.03GB free,
which then broke `qiskit_aer` imports (a real, observed failure, not
hypothetical) until ~2GB was freed. Root cause was NOT primarily the
Docker build (Docker Desktop's own data was only ~7.7GB) - the drive was
apparently already under significant pressure from something else
(possibly a separate Ubuntu WSL installation) that was not fully
identified or touched, out of caution about modifying data outside this
project's scope. Flagged directly to the user rather than guessing further
or deleting things blindly.

**Real screenshots captured** (`docs/screenshots/`, 15 PNGs) of the actual
running frontend against real, populated backend data - login, executive
overview, inventory, asset detail, algorithm explorer, quantum risk (SHAP
factors), PQC recommendations, migration planner + detail, benchmark lab
(real chart + a live-triggered run), quantum lab (real Grover run, 96.53%
success probability, prominent SIMULATOR badge), crypto agility demo,
model registry, audit logs, system health. One real rendering bug was
found and fixed along the way (Recharts pie charts occasionally captured
as empty boxes in headless Chromium due to an animation-timing race) via a
resize-dispatch + poll-for-painted-geometry fix in the capture script
itself, not the app. A second pass fixed a presentation issue (not a bug):
the first full-page captures of list-heavy pages were technically correct
but absurdly tall (07_recommendations.png was 1440x39204px) - retaken as
clean viewport crops for README use. A third pass, while assembling the
README, caught one more real (cosmetic) bug: the Executive Overview page's
algorithm-distribution chart truncated the "HYBRID-ECDH-ML-KEM-768" Y-axis
label to "3RID-ECDH-ML-KEM-768" because the label was wider than the
chart's fixed 160px axis width. Fixed for real in
`frontend/src/pages/OverviewPage.tsx` (widened to 210px, smaller tick
font) - not cropped around or hidden - and the screenshot was retaken,
which also required re-fixing the same pie-chart animation-timing race
found earlier, this time with a stricter wait condition (require every
present chart type's shapes to be painted, not just any one of them,
since the bar chart alone had been satisfying the earlier, looser check
while the pies were still empty).

---

## 2026-09-05 — Closed the last two threat-model gaps: API rate limiting and npm dependency audit

Picked up an in-progress, uncommitted change on disk (backend rate limiting
via `slowapi` + a frontend dark-theme/chart polish pass) and finished it.

**Rate limiting** (`app/core/rate_limit.py`): a `slowapi.Limiter` keyed by
client IP, applied via `@limiter.limit(...)` to `/auth/token` (`10/minute`,
brute-force protection) and the CPU-bound `/benchmarks/run`,
`/quantum/grover/run`, `/quantum/shor/run` endpoints (`30/minute`), with a
generous `300/minute` default elsewhere. This closes the threat model's
previously-**NOT IMPLEMENTED** "API abuse / rate limiting" row.

**A real bug was caught before it shipped**, not after: the limiter was
constructed with `headers_enabled=True` (to emit `X-RateLimit-*` headers),
but slowapi's header-injection path requires the decorated endpoint to
either return a starlette `Response` or declare a `response: Response`
parameter FastAPI can inject headers into. All four decorated routes
return plain dicts and declared no such parameter, so **every single
successful request to any rate-limited endpoint 500'd** on the real running
app — `Exception: parameter 'response' must be an instance of
starlette.responses.Response`. The existing unit tests
(`tests/test_rate_limit.py`) did not catch this because they exercise a
separate, minimal synthetic app that never sets `headers_enabled`, and the
real pytest suite disables the limiter globally (`conftest.py`, so
TestClient's shared fake client host doesn't make the suite itself flaky).
Caught only by manually starting the real `uvicorn` server and hitting
`/api/v1/auth/token` with curl — a login that had been silently broken.
Fixed by adding `response: Response` to `login`, `run_benchmark`,
`grover_run`, and `shor_run`; verified live (200 OK with
`X-RateLimit-Limit`/`X-RateLimit-Remaining` headers present) and added a
regression test (`test_real_login_endpoint_does_not_500_with_rate_limiting_actually_enabled`)
that re-enables the app's real limiter for one request against the real
app and would have failed before this fix. Test count: 68 → 72.

**Dependency audit**: `npm audit --audit-level=high` added as a
non-blocking (`|| true`) CI step alongside the existing `pip-audit`,
closing the threat model's "npm dependencies are not scanned" residual
risk (still non-blocking by design — a finding surfaces for triage, not an
automatic CI failure).

**Frontend theme/chart polish**: a darker, higher-contrast palette
(`frontend/src/index.css`), Inter/JetBrains Mono web fonts, a validated
categorical chart palette shared via `CHART_CATEGORICAL`/`CHART_TOOLTIP_STYLE`
constants (`frontend/src/components/common.tsx`) so every Recharts tooltip
and axis matches the dark surface instead of Recharts' default white box.

**Screenshots regenerated**: the prior session had only re-captured
`01_login.png`/`02_overview.png` against the new theme before stopping; all
15 were re-captured this session (`node scripts/screenshot.mjs` +
`screenshot_crop.mjs`) against the real running app with real, populated
data, matching the current commit's actual appearance.

Verification this session: `pytest -q` → `72 passed, 0 failed`; `tsc -b`
and `vite build` clean; `oxlint` clean (pre-existing fast-refresh warnings
only, unrelated to this change).

---

## Known NOT YET RUN / NOT YET VERIFIED items (as of this log entry)
- **Real quantum hardware execution** has NOT been attempted at all — no
  IBM Quantum/other hardware credential integration exists in this codebase
  (Section 39's "if unavailable, report NOT RUN" applies directly).
- The noise model above was applied to the **Grover lab only**; the Shor lab
  (`app/quantum/shor_lab.py`) does not yet accept a `noise_model` parameter.
- **PostgreSQL** is now verified via a manual run and a dedicated CI job
  (see above) — but the pytest suite's own fixtures (`tests/conftest.py`)
  still hard-code SQLite, so unit/integration test *assertions themselves*
  have still never executed against Postgres, only the demo pipeline has.
- **The full `docker-compose up` stack** (backend + frontend images,
  Prometheus, Grafana all built and running together) was not verified
  end-to-end this session — the backend/frontend image build was aborted
  partway through after it contributed to a critical host disk-space
  incident (see above); only the `postgres` service (pulled, not built)
  was exercised.
- Root cause of the disk-space incident (~190GB of `C:` usage beyond
  Docker's own ~7.7GB) was not fully identified.

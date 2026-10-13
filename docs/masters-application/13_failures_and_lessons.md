# 13. Failures and Lessons

Section 61 requires not hiding failed experiments. This project's
"failures" are mostly expectation mismatches and scope gaps rather than
broken code, and are recorded honestly here.

## 1. XGBoost was expected to win; it didn't
Going into Experiment 3, the natural assumption was that XGBoost — the most
sophisticated of the three trained models — would produce the best
macro-F1. It did not: logistic regression (0.790) beat both XGBoost (0.735)
and barely beat the deterministic rule baseline by less than XGBoost did
(rule baseline 0.723, i.e. XGBoost only outperformed the rule by 0.012).
**Lesson:** on a moderate-size (n=1400 train), low-noise-but-nonlinear
synthetic dataset with a small, well-engineered feature set, a linear model
with the right features can match or beat gradient boosting, which likely
overfits some of its extra flexibility on this sample size. This is
reported as-is per Rule 20, not "fixed" by retuning until XGBoost wins.

## 2. `migration_complexity_ord` turned out to be noise
This feature was included in the model on the reasonable assumption that
migration complexity should matter to risk-prioritization. The ablation
study revealed it is never used in the synthetic label's construction —
so evaluating a model "using" it against a label it has no causal
connection to was, in retrospect, not a fair test of the feature's
real-world value. **Lesson:** an ablation against a *synthetic* label
tells you about the model's behavior on that specific label, not about
whether the feature is inherently useless — this caveat is now stated
explicitly in `11_ablation_studies.md` rather than left implicit.

## 3. `research/experiments/exp6_crypto_agility.py` and `exp8_noise_analysis.py` didn't exist despite being referenced
`backend/agility_demo/README.md` referenced a specific Experiment 6 script
and output table that had never actually been written — a dangling
reference from earlier work in this project's history. This was caught and
fixed during this session's audit pass rather than left as a broken
pointer. **Lesson:** a documentation reference to an experiment is not the
same as having run the experiment; this project now treats "the README
cites it" as a prompt to verify the artifact actually exists, not evidence
that it does.

## 4. `npm run build`/`npm run dev` fail on this specific machine
The repository's absolute path contains a literal `&` character (from the
project's chosen directory name), which breaks Windows' `npm.cmd` shim
(it mis-parses `&` as a shell command separator). Direct invocation of the
underlying binaries (`node_modules/.bin/tsc`, `node_modules/.bin/vite`)
works correctly, and Docker builds are unaffected (no `&` in the container
path). **Lesson:** this is an environment/tooling quirk specific to this
machine's folder naming, not a defect in the frontend code — documented
here rather than silently worked around without explanation.

## 5. Asset-ID join bug in two ablation scripts (caught before either was reported)
`ablation_ai_model.py`'s first version compared two pipeline runs' results
by joining on `Asset.id` — a UUID freshly generated at insert time, and
therefore never equal across two separate temporary databases. The join
silently matched nothing, so every comparison found "0 changes," which
*looked* like a clean, uninteresting null result. It was caught only
because the migration-plan *counts* differed between the two runs (16 vs.
18) despite the (bogus) claim that 0 recommendations had changed — a
direct contradiction, since a differing plan count requires differing
recommendations. **Lesson:** an unexpectedly "clean" negative result
sitting next to an inconsistent secondary number is a specific, checkable
red flag, not just something to note as an unrelated curiosity — pursuing
that inconsistency is what surfaced the real bug. The identical bug was
then found and fixed in `ablation_benchmark_info.py` (written with the
same pattern) *before* it was reported at all, by checking for the same
failure mode proactively once it was known to exist elsewhere in the
codebase. Fixed in both by joining on `hostname` (a stable, config-sourced
value) with an explicit assertion guarding against silent recurrence.

## 6. A PostgreSQL-only VARCHAR truncation bug, invisible under SQLite
`assets.protocol` was declared `VARCHAR(32)`. Real lab config values like
"firmware image signing (long-lived trust anchor)" are 50 characters.
SQLite does not enforce `VARCHAR` length limits at all, so this was never
caught by the (SQLite-only) test suite or by any prior manual run. The
first real PostgreSQL execution this session hit
`psycopg.errors.StringDataRightTruncation` on the very first asset with a
long protocol description. **Lesson:** this is exactly the kind of gap
`ADR-002` had already flagged as an open risk ("SQLite and PostgreSQL are
not behaviorally identical... not independently re-audited") — the
flagging turned out to be justified, and only running against real
Postgres (not just documenting the theoretical risk) actually found the
bug. Fixed by widening the column via a proper Alembic migration, checked
against the longest real value across every config file (not guessed).

## 7. A Docker image build filled the host disk to near-zero free space
Building the `docker-compose` backend/frontend images (Python 3.12-slim +
qiskit/qiskit-aer/xgboost/scipy + Node/nginx layers) drove the host `C:`
drive from some unknown starting point down to 0.03GB free, which then
broke unrelated functionality (`qiskit_aer` failed to import until ~2GB
was freed). Investigation found Docker Desktop's own data was only ~7.7GB
— nowhere near enough to explain ~199GB of usage — strongly suggesting the
drive was already under significant, unrelated pressure (possibly a
separate Ubuntu WSL installation) before this session's build was the
final straw. **Lesson:** the build was aborted, the situation was surfaced
directly to the user rather than continuing to guess at multi-hundred-GB
sources of disk usage inside directories that might contain the user's own
unrelated data, and the full `docker-compose up` stack remains unverified
as a result — recorded as an explicit limitation rather than silently
skipped.

## 8. Scope not reached
Noise analysis was implemented for the Grover lab only, not Shor. Hybrid
signature composition was never implemented (KEM-only). Real quantum
hardware was never attempted (by design — no credentials/integration
exist). The full `docker-compose up` stack (built backend/frontend images
together with Postgres/Prometheus/Grafana) was not verified end-to-end
(see item 7). The pytest suite's own assertions still run against SQLite
only, even though the demo pipeline has now been verified against real
PostgreSQL. See `14_limitations.md` for the complete, current list — all
four Section-40 ablation types and statistical significance testing, both
originally gaps here, were subsequently built and are covered in
`11_ablation_studies.md` and `09_ai_risk_experiments.md`.

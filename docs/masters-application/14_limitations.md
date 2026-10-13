# 14. Limitations

Per Section 60, stated without hedging.

## Data limitations
- **No real enterprise cryptographic inventory.** The 42-asset "enterprise
  lab" is hand-authored/seeded synthetic lab data (`backend/enterprise_lab/`),
  not a real organization's discovered assets.
- **No real risk-priority ground truth.** The AI risk model is trained on a
  synthetic label with a documented, arguably arbitrary formula — it has
  never been validated against real migration-urgency outcomes, because
  none exist for this project. The label-construction methodology is
  sound (a falsifiable, non-circular test of whether ML recovers withheld
  structure), but "the model predicts synthetic-label structure well" is
  not the same claim as "the model predicts real-world urgency well."
- **No real migration-effort ground truth.** The 1183-hour total from
  Experiment 10 comes from an engineering-judgment formula, not from
  calibration against completed real migrations.

## Quantum limitations
- **Scale.** All quantum experiments are capped at 16 qubits by design —
  they demonstrate algorithmic mechanics, not anything approaching
  cryptographically relevant scale.
- **No real hardware.** Every quantum result is a classical simulation.
  Real NISQ hardware execution, let alone fault-tolerant hardware, was
  never attempted — no credentials/integration exist in this codebase.
- **Noise model realism.** The Experiment 8 noise model uses illustrative,
  not device-calibrated, error rates.

## PQC / cryptography limitations
- **Implementation source.** `pqcrypto`'s PQClean-derived builds are used
  rather than a from-scratch or vendor-certified implementation — standard
  practice for research use, but not the same assurance level as a
  FIPS-140-validated module.
- **Hybrid signatures not implemented** — only hybrid key exchange exists.
- **No real TLS termination** — the `CryptoProvider` abstraction operates
  at the primitive level; no real protocol handshake is exercised.
- **Benchmark hardware dependence.** All benchmark numbers are specific to
  the development machine they were run on; they are internally comparable
  (same machine, same run) but not necessarily representative of
  production hardware, especially for PQC implementations whose relative
  performance can shift on hardware with different AES-NI/vector
  instruction support.

## AI/ML limitations
- **No hyperparameter tuning.** Fixed hyperparameters throughout; the
  model comparison reflects untuned defaults, not each algorithm's best
  achievable performance. (Statistical significance testing *was* added —
  see below — but it characterizes the untuned comparison, not a
  tuned-ceiling one.)
- **SHAP scaling.** Per-asset SHAP explanation cost was not benchmarked at
  bulk-inventory scale.
- **Benchmark-info ablation scope.** The recommendation engine's use of
  real benchmark data only applies to one specific condition (long-lived,
  internet-facing TLS-certificate signature assets) — extending it to
  other usage types/strategies is real future work, not implemented.

## Engineering / infrastructure limitations
- **PostgreSQL: pipeline verified, pytest suite still SQLite-only.** A real
  `docker-compose` Postgres instance was migrated and exercised end-to-end
  via `scripts.run_demo` (catching and fixing a real `VARCHAR(32)`-too-
  narrow bug SQLite silently tolerated — see `13_failures_and_lessons.md`
  and `ADR-002`), and a dedicated CI job now runs this automatically. The
  pytest suite's own *assertions*, however, still run against
  `tests/conftest.py`'s hard-coded SQLite fixture — no test has directly
  asserted against Postgres, only the demo pipeline has.
- **Full `docker-compose up` stack unverified.** Building the backend/
  frontend Docker images was aborted after contributing to a critical
  host disk-space incident (`C:` drive dropped to 0.03GB free, breaking
  `qiskit_aer` imports until space was freed) — see below. Only the
  `postgres` service (a pulled, not built, image) was exercised live.
- **Frontend browser verification.** Real screenshots (`docs/screenshots/`)
  were captured via headless Playwright against a live backend with real
  data (not mocked), and visually spot-checked — a stronger verification
  than the type/API-matching used in the first build session, though still
  not a full manual QA pass across every interaction and edge case.
- **Windows path quirk.** A literal `&` in this repository's folder name
  breaks the Windows `npm.cmd` shim for this specific checkout — an
  environment artifact, not a portability guarantee failure, but worth
  knowing if reproducing on Windows under this exact path.
- **Host disk-space incident, root cause not fully identified.** A Docker
  image build filled the host `C:` drive to near-zero free space during
  this session. Docker Desktop's own data accounted for only ~7.7GB of the
  ~199GB used — the remainder (likely a separate Ubuntu WSL installation
  on the host) was not investigated further, out of caution about touching
  data outside this project's scope. This is a host-environment issue, not
  a defect in the project, but is recorded here because it did interrupt
  work (see `research/RESEARCH_LOG.md`) and would recur if the full
  `docker-compose` image build were retried without addressing host disk
  space first.

## Standards-currency limitation
This project references FIPS 203/204/205 (finalized August 2024) as the
current PQC standards at time of writing (2026). Cryptographic standards
are revised; anyone extending this project should re-check NIST's current
guidance rather than assume this project's algorithm choices remain
current indefinitely (Section 64).

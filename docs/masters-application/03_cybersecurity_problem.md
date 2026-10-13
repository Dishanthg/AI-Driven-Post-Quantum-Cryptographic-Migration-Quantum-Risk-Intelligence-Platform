# 03. Cybersecurity Problem

## The problem
Organizations do not have a clean, current inventory of where and how they
use public-key cryptography. Certificates, TLS configs, key-exchange
settings, and signature algorithms accumulate across services over years,
often installed by different teams at different times, rarely revisited
until something breaks. A quantum-safe migration cannot start from "we
think we mostly use RSA-2048 and some newer stuff uses ECC" — it needs a
real inventory, a way to say which of those assets matter most, a
technically sound recommendation for what to move each one to, and a way to
estimate the cost/risk of actually doing it. Section 0's problem statement
puts this precisely: *"How can organizations identify cryptographically
vulnerable infrastructure, estimate its exposure to future quantum threats,
prioritize migration, and evaluate post-quantum alternatives while
balancing security, performance, compatibility and operational
complexity?"*

## Why this is a systems problem, not just a cryptography problem
Picking ML-KEM over RSA is the easy part once you know an asset needs to
move. The hard parts are: (1) knowing the asset exists and what it's used
for; (2) deciding whether it's worth moving now, later, or via a hedged
hybrid strategy, given that migration has real engineering cost and real
compatibility risk; (3) having evidence — not intuition — for the
performance and size trade-offs a target algorithm introduces; (4) building
systems so the *next* migration (because there will be a next one — PQC
standards are young and NIST's own guidance anticipates revision) doesn't
require another multi-year, ground-up effort.

## How QuantumShield addresses each part
1. **Discovery/inventory** — `backend/app/discovery/scanner.py` reads
   controlled configuration sources into a relational inventory (`asset`,
   `application`, `certificate`, `cryptographic_usage` tables).
2. **Prioritization** — both a transparent rule baseline
   (`backend/app/ai/rule_baseline.py`) and a trained, SHAP-explained ML
   model (`backend/app/ai/train.py`, `explain.py`), compared honestly
   against each other rather than assuming the more sophisticated approach
   wins (it didn't — see `05_hypotheses.md`, H1 discussion).
3. **Recommendation** — a deterministic, explained engine
   (`backend/app/recommendations/engine.py`) producing one of five
   strategies (`pqc_migration`, `hybrid_migration`, `deferred`,
   `agility_prep`, `manual_review`), each with rationale/assumptions/
   trade-offs text surfaced verbatim, never re-authored by the UI.
4. **Evidence for trade-offs** — a real benchmark harness across 13
   algorithms/compositions (classical, PQC, hybrid), not asserted numbers
   (`research/tables/benchmark_sweep.csv`).
5. **Agility for the next migration** — the `CryptoProvider` abstraction and
   a measured demonstration (Experiment 6) that a provider-abstracted
   service needs zero business-logic changes to swap algorithms, versus 4
   hard-wired call sites in a tightly-coupled comparison design.

## What is deliberately out of scope
QuantumShield does not scan real production networks, real certificates
from the public internet, or any system the operator doesn't explicitly
control and configure as a lab target (Section 7's discovery-scope rule).
It does not terminate real TLS connections during migration simulation —
the `CryptoProvider` interface operates at the cryptographic-primitive
level, and the migration simulator models stage transitions and benchmarks
them, but does not modify any live service.

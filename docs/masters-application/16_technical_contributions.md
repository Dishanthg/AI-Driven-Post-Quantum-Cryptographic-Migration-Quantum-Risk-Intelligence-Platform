# 16. Technical Contributions

What was actually engineered, distinct from what was merely configured or
assembled from libraries.

## Novel-to-this-project engineering (not "just calling a library")
- **Falsifiable synthetic-label methodology for AI risk research**
  (`app/ai/dataset.py`): a label formula with a documented, withheld
  nonlinear interaction term, specifically designed so "can ML recover
  structure a linear rule can't see" is testable rather than assumed —
  this is a research-design contribution, not just a data generator.
- **Structural (not just documented) quantum-scope safety**
  (`ADR-006`): the qubit cap is enforced by a raising check inside the lab
  function itself, at every entry point (direct call, CLI, API), and is
  covered by a dedicated regression test asserting the Shor lab's own
  result text never implies RSA has been broken. This is a concrete
  engineering answer to a genuinely hard problem (how do you make a "don't
  overstate quantum capability" promise enforceable rather than aspirational).
- **Hash-verified, not asserted, crypto-agility measurement**
  (`research/experiments/exp6_crypto_agility.py`): "zero code changes"
  is proven by SHA-256 equality of the business-logic file before and
  after three real algorithm swaps with real roundtrip verification at
  each step — not a claim, a check.
- **SHAP explainability unified across model classes**
  (`app/ai/explain.py`): one module correctly handles both SHAP's
  older (list-of-arrays) and newer (stacked 3D array) output shapes for
  tree ensembles, and falls back to exact coefficient-based attribution
  for linear models — without requiring per-model-class explanation code
  elsewhere in the system.
- **Deterministic, formula-transparent migration-effort estimation**
  (`app/migration/planner.py`): every plan ships the exact arithmetic
  string that produced its hour estimate, not just the number — an
  explicit design choice to keep an admittedly-uncalibrated estimate
  auditable rather than opaque.

## Integration engineering
- A working `CryptoProvider` abstraction spanning 4 classical primitives
  (RSA, ECDSA, ECDH, DH), 7 standardized PQC algorithms (3 ML-KEM variants,
  3 ML-DSA variants, SLH-DSA-SHA2-128f), and 1 hybrid composition, behind
  one interface, benchmarked uniformly.
- A ~20-entity relational schema (Alembic-migrated) supporting both SQLite
  (dev/test) and PostgreSQL (docker-compose) without code changes.
- An 11-router, JWT+RBAC-secured FastAPI layer, and a 13-page
  TypeScript/React frontend whose types mirror the backend's Pydantic
  schemas field-for-field, with zero mocked data anywhere in the UI.
- CI (lint + full 66-test suite + dependency audit) and a lint-clean
  (`ruff check`) backend codebase.

## What is explicitly *not* claimed as a contribution
No novel cryptographic primitive, no novel PQC algorithm, and no novel
quantum algorithm are introduced anywhere in this project — Rule 6
prohibits from-scratch primitive implementation, and none was attempted.
The contribution is in the system design, the measurement methodology, and
the discipline of not overstating any of it — not in cryptographic or
quantum-algorithmic research itself.

# ADR-007: Deterministic, role-authorized migration actions — no LLM in the authorization path

## Status
Accepted, implemented (`backend/app/core/security.py`,
`backend/app/api/deps.py`, `backend/app/migration/planner.py`).

## Context
Section 51 ("AI Security") is explicit: an LLM may explain and assist but
must never itself change cryptographic configuration, execute commands,
deploy infrastructure, or modify certificates — all changes must pass
deterministic validation and authorization. QuantumShield doesn't currently
embed an LLM in the runtime path at all (recommendations/explanations are
either deterministic rules or SHAP attributions over a trained classifier,
not generative text from a language model) — but the migration planner and
simulator are exactly the kind of "propose a change to cryptographic
posture" component this rule is aimed at, so the authorization boundary
needed to be real before any such integration is ever considered.

## Problem
What actually gates "a migration plan gets created/simulated," and is that
gate enforceable independent of whatever produced the recommendation (rule
engine today, potentially an LLM-assisted explanation layer later)?

## Alternatives considered
- **Trust the caller / no role check, rely on network perimeter.** Rejected
  — Section 50 requires RBAC and least privilege; a network boundary is not
  an authorization boundary.
- **Authorize based on which module produced the recommendation** (e.g.
  "trust anything from `recommendations/engine.py`"). Rejected — this
  conflates "is this content well-formed" with "is this actor allowed to
  act," which is exactly the confusion Section 51 warns against for a future
  LLM-assisted layer: content provenance is not authorization.
- **Soft warnings only (log but don't block) for non-admin migration
  triggers.** Rejected — Section 24/26 requires migrations to have a
  verification/rollback story and a real owner; an unenforced warning is not
  a control.

## Decision
- `app/core/security.py` is the *only* module that mints or verifies JWTs.
  Three roles are defined (`ROLE_VIEWER`, `ROLE_ANALYST`, `ROLE_ADMIN`) with
  `require_role(*roles)` as the single composable authorization primitive.
- `app/api/deps.py` exposes exactly three composite dependencies used across
  every router: `require_viewer` (read-only, any authenticated user),
  `require_analyst` (can trigger scans/assessments/migrations/simulations),
  `require_admin`.
- State-changing migration endpoints (`POST /api/v1/migrations/.../plan`,
  `/plan-all`, `/{id}/simulate`, `/simulate-all`) all depend on
  `require_analyst` or stricter — never on `require_viewer` alone, and never
  on an unauthenticated or content-based check.
- Effort/priority/target-algorithm values that feed the plan are themselves
  deterministic (rule-based recommendation engine, documented formula for
  effort estimation in `migration/planner.py` — see its module docstring) —
  there is currently no generative/LLM component anywhere in this path for
  the authorization boundary to be bypassed around.
- `app/api/audit.py` records actor, action, and before/after state for
  auditable actions, so an authorized change is also traceable after the
  fact (Section 14: Audit System).

## Consequences
- Positive: the authorization boundary does not depend on trusting the
  content of a recommendation — only on the authenticated caller's role,
  which is exactly the property Section 51 requires ahead of any future
  LLM-assisted explanation feature.
- Positive: this is unit-testable and tested independent of the
  recommendation logic itself (RBAC dependency is a single reusable
  function, not duplicated per-router).
- Explicit non-claim: this ADR does not mean an LLM has been "added safely"
  — no LLM currently sits in this runtime path at all. This ADR documents
  the boundary that any future LLM-assisted layer (e.g. natural-language
  explanation of a recommendation) would have to sit behind, not an existing
  integration.

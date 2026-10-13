"""API rate limiting (design doc Section 50: "Implement... rate limiting" -
previously a documented, unaddressed gap in docs/security/threat-model.md).

Uses slowapi (a maintained wrapper around the `limits` library) - an
established, vetted rate-limiting library, not a hand-rolled token bucket.
Keyed by client IP (in-memory storage; a multi-process/multi-instance
deployment would need a shared backend such as Redis - noted as a scaling
limitation, not implemented here since this is a single-process dev/lab
deployment).

Two tiers are applied where it matters, not a blanket limit everywhere:
- AUTH_LIMIT: brute-force protection on the login endpoint.
- EXPENSIVE_LIMIT: protects the quantum-lab and benchmark endpoints, which
  trigger real CPU-bound computation (Qiskit Aer simulation, PQC keygen/
  sign/verify loops) per request - an attacker (or a buggy client) hammering
  these could otherwise cause real resource exhaustion even without any
  application-logic bug.
Every other route falls under the Limiter's generous default, a safety net
rather than a tight throttle.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

AUTH_LIMIT = "10/minute"
EXPENSIVE_LIMIT = "30/minute"
DEFAULT_LIMITS = ["300/minute"]

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=DEFAULT_LIMITS,
    enabled=get_settings().rate_limit_enabled,
    headers_enabled=True,
)

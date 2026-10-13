"""SYNTHETIC DATA generator for the AI risk engine's training set.

*** This is not real organizational data. Every row is generated. ***

Design rationale (design doc Section 21, "document how labels are
constructed"): the synthetic "true priority" label is deliberately built to
include a nonlinear interaction term (internet exposure x data sensitivity)
and Gaussian noise that a simple linear rule cannot fully capture. This is a
methodological choice, not an attempt to make the ML model look artificially
good: it lets Experiment 3/4 ask a meaningful, falsifiable question - "can a
model recover interaction structure that a linear heuristic misses, on data
where such structure demonstrably exists" - rather than a tautological one. The
rule-based baseline (app/ai/rule_baseline.py) is a SEPARATE, simpler, linear
scorer that a real organization could plausibly hand-write; it is not given
access to the label formula.

Every value in the generated table is produced by this function at run time
with a fixed random seed for reproducibility; nothing is a literal hard-coded
per-row constant.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ai.features import ORDINAL_MAP, QUANTUM_VULN_MAP
from app.crypto.registry import all_specs

_ALGO_IDS = [s.id for s in all_specs() if s.provider_key or s.classification in ("classical_pk", "classical_sym", "hash")]
_ORDINALS = list(ORDINAL_MAP.keys())
_QVULN_ALGOS = {s.id: s.quantum_vulnerability for s in all_specs()}
_KEYSIZE_ALGOS = {s.id: (s.typical_key_size_bits or 256) for s in all_specs()}

LABEL_WEIGHTS = {
    "quantum_vulnerability": 0.28,
    "asset_criticality": 0.20,
    "data_sensitivity": 0.14,
    "data_lifetime_years_norm": 0.10,
    "internet_exposure": 0.13,
    "business_importance": 0.10,
    "interaction_exposure_sensitivity": 0.15,  # nonlinear term, deliberately withheld from the rule baseline
}
NOISE_STD = 0.06
PRIORITY_THRESHOLDS = {"critical": 0.72, "high": 0.55, "medium": 0.35}  # else "low"


def _priority_from_score(score: float) -> str:
    if score >= PRIORITY_THRESHOLDS["critical"]:
        return "critical"
    if score >= PRIORITY_THRESHOLDS["high"]:
        return "high"
    if score >= PRIORITY_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def true_risk_score(row: dict) -> float:
    qv = QUANTUM_VULN_MAP[row["quantum_vulnerability"]] / 2.0
    crit = ORDINAL_MAP[row["asset_criticality"]] / 3.0
    sens = ORDINAL_MAP[row["data_sensitivity"]] / 3.0
    lifetime = min(1.0, row["data_lifetime_years"] / 20.0)
    exposure = 1.0 if row["internet_exposure"] else 0.0
    business = ORDINAL_MAP[row["business_importance"]] / 3.0

    score = (
        LABEL_WEIGHTS["quantum_vulnerability"] * qv
        + LABEL_WEIGHTS["asset_criticality"] * crit
        + LABEL_WEIGHTS["data_sensitivity"] * sens
        + LABEL_WEIGHTS["data_lifetime_years_norm"] * lifetime
        + LABEL_WEIGHTS["internet_exposure"] * exposure
        + LABEL_WEIGHTS["business_importance"] * business
        + LABEL_WEIGHTS["interaction_exposure_sensitivity"] * exposure * sens
    )
    return float(np.clip(score, 0.0, 1.0))


def generate_synthetic_inventory(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """SYNTHETIC DATA. Returns a DataFrame of n synthetic cryptographic assets with
    a documented, noisy, nonlinear-interaction ground-truth priority label."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        algo_id = rng.choice(_ALGO_IDS)
        row = {
            "algorithm_id": algo_id,
            "quantum_vulnerability": _QVULN_ALGOS[algo_id],
            "key_size_bits": _KEYSIZE_ALGOS[algo_id],
            "asset_criticality": rng.choice(_ORDINALS, p=[0.25, 0.35, 0.28, 0.12]),
            "data_sensitivity": rng.choice(_ORDINALS, p=[0.20, 0.35, 0.30, 0.15]),
            "data_lifetime_years": int(rng.integers(1, 21)),
            "internet_exposure": bool(rng.choice([True, False], p=[0.4, 0.6])),
            "migration_complexity": rng.choice(["low", "medium", "high"], p=[0.3, 0.45, 0.25]),
            "business_importance": rng.choice(_ORDINALS, p=[0.20, 0.30, 0.30, 0.20]),
        }
        clean_score = true_risk_score(row)
        noisy_score = float(np.clip(clean_score + rng.normal(0, NOISE_STD), 0.0, 1.0))
        row["true_risk_score"] = noisy_score
        row["priority_label"] = _priority_from_score(noisy_score)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


DATASET_CARD = """
DATASET: synthetic_crypto_inventory
LABEL: SYNTHETIC DATA (see design doc Rule 14) - NOT real organizational ground truth.
GENERATION: app.ai.dataset.generate_synthetic_inventory(n, seed) using numpy's
Generator(PCG64) seeded PRNG; fully reproducible for a fixed seed.
LABEL CONSTRUCTION: documented weighted sum with an explicit nonlinear
interaction term (internet_exposure * data_sensitivity) plus Gaussian noise
(std=0.06), discretized into {low, medium, high, critical} via fixed
thresholds (see PRIORITY_THRESHOLDS). Intended to test whether ML models can
recover structure a simple linear heuristic cannot - not to represent
validated real-world risk.
"""

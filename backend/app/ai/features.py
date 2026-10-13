"""Shared feature schema for the AI risk engine (design doc Section 19).

Both the rule baseline and the ML models consume exactly this feature vector,
so their comparison (Experiment 3/4) is apples-to-apples. Ordinal categorical
fields are encoded 0..3 (low/medium/high/critical) with the mapping documented
here, not scattered across call sites.
"""
from __future__ import annotations

from dataclasses import dataclass

ORDINAL_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
QUANTUM_VULN_MAP = {"not_significantly_affected": 0, "quantum_weakened": 1, "quantum_vulnerable": 2}

FEATURE_NAMES = [
    "quantum_vulnerability",     # 0/1/2 - from AlgorithmRegistry classification
    "key_size_norm",             # key size normalized to [0,1] against a 4096-bit reference
    "asset_criticality",         # 0-3
    "data_sensitivity",          # 0-3
    "data_lifetime_years_norm",  # normalized against a 20-year reference
    "internet_exposure",         # 0/1
    "migration_complexity",      # 0-2 (low/medium/high) - included as a feature but NOT part of true-risk
                                  # label construction (see dataset.py); an ablation ("remove migration_complexity")
                                  # should show near-zero impact, which is itself a validity check on the model.
    "business_importance",       # 0-3
]


@dataclass
class AssetFeatures:
    quantum_vulnerability: int
    key_size_norm: float
    asset_criticality: int
    data_sensitivity: int
    data_lifetime_years_norm: float
    internet_exposure: int
    migration_complexity: int
    business_importance: int

    def to_vector(self) -> list[float]:
        return [
            self.quantum_vulnerability, self.key_size_norm, self.asset_criticality,
            self.data_sensitivity, self.data_lifetime_years_norm, self.internet_exposure,
            self.migration_complexity, self.business_importance,
        ]

    @staticmethod
    def from_raw(
        quantum_vulnerability: str, key_size_bits: int, asset_criticality: str,
        data_sensitivity: str, data_lifetime_years: int, internet_exposure: bool,
        migration_complexity: str, business_importance: str,
    ) -> AssetFeatures:
        return AssetFeatures(
            quantum_vulnerability=QUANTUM_VULN_MAP[quantum_vulnerability],
            key_size_norm=min(1.0, key_size_bits / 4096.0),
            asset_criticality=ORDINAL_MAP[asset_criticality],
            data_sensitivity=ORDINAL_MAP[data_sensitivity],
            data_lifetime_years_norm=min(1.0, data_lifetime_years / 20.0),
            internet_exposure=1 if internet_exposure else 0,
            migration_complexity=ORDINAL_MAP.get(migration_complexity, 1) if migration_complexity != "critical" else 2,
            business_importance=ORDINAL_MAP[business_importance],
        )

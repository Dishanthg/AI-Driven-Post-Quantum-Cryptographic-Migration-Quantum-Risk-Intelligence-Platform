"""Generates enterprise_lab/configs/internal-mesh.yaml: a fleet of small
internal microservices with mTLS/key-exchange configuration.

SYNTHETIC LAB DATA - documented here, not real service inventory. Unlike
`app.ai.dataset` (which generates *training* data for the risk model with a
documented ground-truth label formula), this script only samples which
*configuration* each of N fictional internal services happens to run and its
descriptive attributes (criticality/sensitivity/exposure/etc.) - it assigns no
risk label. Deterministic for a fixed seed via numpy's Generator(PCG64).

Algorithm sampling weights (documented, not hidden): mirrors a fleet that is
mostly on modern classical mTLS, with a legacy DH holdout and a small
already-migrated PQC/hybrid slice - a plausible mid-migration snapshot.

Run: python -m enterprise_lab.generate_mesh [--n 18] [--seed 42]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import yaml

ALGO_WEIGHTS = {
    "ECDSA-P256": 0.45,
    "ECDH-P256": 0.20,
    "RSA-2048": 0.15,
    "DH-2048": 0.10,
    "ML-KEM-768": 0.06,
    "HYBRID-ECDH-ML-KEM-768": 0.04,
}
USAGE_BY_ALGO = {
    "ECDSA-P256": "tls_certificate",
    "RSA-2048": "tls_certificate",
    "ECDH-P256": "key_exchange",
    "DH-2048": "key_exchange",
    "ML-KEM-768": "key_exchange",
    "HYBRID-ECDH-ML-KEM-768": "key_exchange",
}
STATUS_BY_ALGO = {
    "ECDSA-P256": "legacy", "RSA-2048": "legacy", "ECDH-P256": "legacy", "DH-2048": "legacy",
    "ML-KEM-768": "pqc_migrated", "HYBRID-ECDH-ML-KEM-768": "hybrid",
}
SERVICE_NAMES = [
    "inventory-svc", "shipping-svc", "pricing-svc", "search-svc", "recommendation-svc",
    "notification-svc", "analytics-svc", "audit-svc", "billing-svc", "catalog-svc",
    "fraud-detection-svc", "session-cache-svc", "feature-flag-svc", "reporting-svc",
    "webhook-dispatch-svc", "config-svc", "scheduler-svc", "media-processing-svc",
]
CRITICALITY_LEVELS = ["low", "medium", "high", "critical"]
SENSITIVITY_LEVELS = ["low", "medium", "high", "critical"]
MIGRATION_LEVELS = ["low", "medium", "high"]


def generate(n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    algos = list(ALGO_WEIGHTS.keys())
    weights = list(ALGO_WEIGHTS.values())

    names = rng.choice(SERVICE_NAMES, size=min(n, len(SERVICE_NAMES)), replace=False)
    if n > len(SERVICE_NAMES):
        names = list(names) + [f"internal-svc-{i:02d}" for i in range(n - len(SERVICE_NAMES))]

    assets = []
    for name in names:
        algo = str(rng.choice(algos, p=weights))
        assets.append({
            "hostname": f"{name}-01",
            "usage_type": USAGE_BY_ALGO[algo],
            "protocol": "internal mTLS",
            "algorithm_id": algo,
            "data_sensitivity": str(rng.choice(SENSITIVITY_LEVELS, p=[0.25, 0.40, 0.25, 0.10])),
            "data_lifetime_years": int(rng.integers(1, 6)),
            "asset_criticality": str(rng.choice(CRITICALITY_LEVELS, p=[0.15, 0.40, 0.35, 0.10])),
            "internet_exposure": bool(rng.choice([True, False], p=[0.05, 0.95])),  # internal mesh, rarely internet-facing
            "migration_complexity": str(rng.choice(MIGRATION_LEVELS, p=[0.35, 0.45, 0.20])),
            "current_status": STATUS_BY_ALGO[algo],
        })

    return {
        "application": {
            "name": "internal-mesh",
            "business_unit": "platform",
            "business_importance": "medium",
            "description": (
                f"SYNTHETIC LAB DATA - {n} generated internal microservices "
                f"(seed={seed}); see enterprise_lab/generate_mesh.py for sampling weights."
            ),
        },
        "assets": assets,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=18)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    doc = generate(args.n, args.seed)
    out_path = Path(__file__).parent / "configs" / "internal-mesh.yaml"
    header = (
        "# GENERATED FILE - SYNTHETIC LAB DATA. Do not hand-edit; regenerate via\n"
        "# `python -m enterprise_lab.generate_mesh`. See enterprise_lab/README.md.\n"
    )
    out_path.write_text(header + yaml.dump(doc, sort_keys=False))
    print(f"Wrote {len(doc['assets'])} assets to {out_path}")


if __name__ == "__main__":
    main()

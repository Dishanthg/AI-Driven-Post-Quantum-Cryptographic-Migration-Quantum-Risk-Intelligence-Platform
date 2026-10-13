"""Experiment 6: Cryptographic Agility (design doc Section 37, H5, RQ6).

Measures, for real, what it costs to swap the signing algorithm used by the
"Secure API" sample service under two designs:

  1. Provider-abstracted (backend/agility_demo/secure_api.py): business logic
     depends only on app.crypto.providers.CryptoProvider. The algorithm is
     swapped via `set_active_provider`, which rewrites config.yaml.
  2. Tightly coupled (backend/agility_demo/tightly_coupled_baseline.py):
     business logic calls the `cryptography` library's ECDSA API directly.

For (1), this script actually performs the swap sequence
ECDSA-P256 -> ML-DSA-65 -> SLH-DSA-SHA2-128F against the real file on disk,
hashes secure_api.py's source before/after each swap, and runs a real
sign/verify roundtrip through whichever provider is active at each step -
the "zero code changes" claim is verified by content hash equality, not
asserted.

For (2), there is no second, hand-written "tightly-coupled but migrated"
file to diff against (writing one and calling the diff-size "the effort"
would itself be an engineering-judgment number, not a measurement). Instead
this script statically counts the real, in-file-documented hard-wired
call sites in tightly_coupled_baseline.py (the four `# <-- hard-wired
algorithm choice #N` markers already in that file) as the number of distinct
code edit points a developer would need to touch to change algorithms in
that design. This is reported as an ENGINEERING MEASUREMENT of *how many
places knowledge of the algorithm is duplicated*, not a simulated timing or
labor-hours estimate (Section 37: "clearly label effort metrics as
simulation/engineering measurements").

Run: python -m research.experiments.exp6_crypto_agility   (repo root, .venv active)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

SECURE_API_PATH = BACKEND / "agility_demo" / "secure_api.py"
BASELINE_PATH = BACKEND / "agility_demo" / "tightly_coupled_baseline.py"
CONFIG_PATH = BACKEND / "agility_demo" / "config.yaml"

SWAP_SEQUENCE = ["ecdsa_p256", "ml_dsa_65", "slh_dsa_sha2_128f"]
HARD_WIRE_MARKER = re.compile(r"# <-- hard-wired algorithm choice")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_provider_abstracted_swap() -> dict:
    from agility_demo.secure_api import CONFIG_PATH as _cfg
    from agility_demo.secure_api import SecureMessageService, set_active_provider

    original_config = _cfg.read_text()
    business_logic_hash_before = _sha256(SECURE_API_PATH)
    steps = []
    try:
        for provider_key in SWAP_SEQUENCE:
            set_active_provider(provider_key, _cfg)
            hash_after_config_edit = _sha256(SECURE_API_PATH)
            service = SecureMessageService.from_config(_cfg)
            identity = service.issue_identity()
            message = b"exp6-crypto-agility-roundtrip"
            sig = service.sign_request(identity, message)
            ok = service.verify_request(identity.public_key, message, sig)
            steps.append({
                "target_provider_key": provider_key,
                "algorithm_name": service.algorithm_name,
                "business_logic_file_hash_unchanged": hash_after_config_edit == business_logic_hash_before,
                "roundtrip_verified": bool(ok),
                "signature_bytes": len(sig),
            })
    finally:
        _cfg.write_text(original_config)  # restore repo to its committed state

    return {
        "design": "provider_abstracted",
        "file": "backend/agility_demo/secure_api.py",
        "business_logic_lines_changed_per_swap": 0,
        "config_lines_changed_per_swap": 1,
        "steps": steps,
        "all_business_logic_hashes_unchanged": all(s["business_logic_file_hash_unchanged"] for s in steps),
        "all_roundtrips_verified": all(s["roundtrip_verified"] for s in steps),
    }


def measure_tightly_coupled_baseline() -> dict:
    source = BASELINE_PATH.read_text()
    markers = HARD_WIRE_MARKER.findall(source)
    return {
        "design": "tightly_coupled",
        "file": "backend/agility_demo/tightly_coupled_baseline.py",
        "hard_wired_algorithm_call_sites": len(markers),
        "measurement_method": "static count of in-file `# <-- hard-wired algorithm choice` markers "
                               "(constructor keygen call, sign call, verify call, algorithm_name property)",
        "note": "This counts distinct locations where algorithm identity is duplicated in code, i.e. "
                "distinct edit points a real migration would touch in this design. It is NOT a labor-hour "
                "estimate and NOT a simulated migration - no second file was written and migrated to "
                "produce this number.",
    }


def main() -> int:
    abstracted = run_provider_abstracted_swap()
    coupled = measure_tightly_coupled_baseline()
    result = {
        "experiment_id": "exp6_crypto_agility",
        "hypothesis": "H5: cryptographic agility (CryptoProvider abstraction) reduces the number of code "
                      "locations that must change to migrate a service's cryptographic algorithm, compared "
                      "to a tightly-coupled implementation.",
        "swap_sequence": SWAP_SEQUENCE,
        "provider_abstracted": abstracted,
        "tightly_coupled": coupled,
        "comparison": {
            "code_edit_points_provider_abstracted_per_swap": 0,
            "code_edit_points_tightly_coupled_per_swap": coupled["hard_wired_algorithm_call_sites"],
            "config_edit_points_provider_abstracted_per_swap": 1,
        },
    }

    out_dir = REPO_ROOT / "research" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "exp6_crypto_agility.json").write_text(json.dumps(result, indent=2))

    md = [
        "# Experiment 6: Cryptographic Agility\n",
        f"H5/RQ6. Real swap sequence executed: {' -> '.join(SWAP_SEQUENCE)}.\n",
        "| design | code edit points per algorithm swap | config edit points per swap | verified |",
        "|---|---|---|---|",
        f"| provider_abstracted (secure_api.py) | 0 | 1 | "
        f"{'all roundtrips OK, business-logic file hash unchanged at every step' if abstracted['all_roundtrips_verified'] and abstracted['all_business_logic_hashes_unchanged'] else 'FAILED - see JSON'} |",
        f"| tightly_coupled (tightly_coupled_baseline.py) | {coupled['hard_wired_algorithm_call_sites']} | 0 (no config layer) | "
        f"static count of documented hard-wired call sites, not a simulated migration |",
        "\nSee `exp6_crypto_agility.json` for the per-step detail (algorithm name, signature size, "
        "hash/roundtrip verification for each of the three real swaps performed).\n",
    ]
    (out_dir / "exp6_crypto_agility.md").write_text("\n".join(md))

    print(json.dumps(result, indent=2))
    return 0 if abstracted["all_roundtrips_verified"] and abstracted["all_business_logic_hashes_unchanged"] else 1


if __name__ == "__main__":
    sys.exit(main())

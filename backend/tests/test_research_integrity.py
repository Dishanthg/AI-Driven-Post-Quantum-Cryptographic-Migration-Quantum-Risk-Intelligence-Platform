"""Automated guard for design doc Section 63/76 ("do not claim RSA/AES/ECC
have been broken"). Scans the app package's source for a conservative list of
affirmative-claim phrases that would only appear in a false claim - not for
the (correct, present-throughout) negated caveats like "does not mean RSA is
broken", which this deliberately does not flag."""
from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_PHRASES = [
    "successfully broke rsa",
    "we broke rsa",
    "have broken rsa",
    "cracked rsa",
    "cracked aes",
    "broke aes",
    "defeated aes",
    "quantum supremacy achieved",
    "can break rsa-2048",
    "can break rsa-4096",
    "practical quantum supremacy",
]


def test_no_forbidden_overclaiming_phrases_in_source():
    violations = []
    for path in APP_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                violations.append(f"{path.relative_to(APP_DIR.parent)}: contains forbidden phrase {phrase!r}")
    assert not violations, "\n".join(violations)


def test_quantum_lab_results_are_always_labeled():
    """Every dataclass result object the quantum labs produce must carry an
    explicit data_label / hardware_type so no caller can present a simulation
    as real hardware without the label being visibly wrong."""
    from app.quantum.grover_lab import run_grover
    from app.quantum.shor_lab import factor_via_shor

    g = run_grover(n_qubits=3, marked_states=[1], shots=256)
    assert g.data_label == "QUANTUM SIMULATION"
    assert g.hardware_type == "SIMULATOR"

    s = factor_via_shor(15)
    assert s.data_label == "QUANTUM SIMULATION"
    assert s.hardware_type == "SIMULATOR"

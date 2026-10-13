"""Comparison artifact for Experiment 6 ONLY - never imported by the actual
sample service. This is what `secure_api.py` would look like WITHOUT the
CryptoProvider abstraction: the signing algorithm is hard-wired directly
against `cryptography`'s ECDSA API, inline in the business logic.

To "migrate" this version to ML-DSA-65 you would have to edit this file's
imports, key-generation call, sign call, and verify call - four separate code
edits versus `secure_api.py`'s one YAML value. Experiment 6
(research/experiments/exp6_crypto_agility.py) uses a naive diff between this
file and a hand-written ML-DSA equivalent as the "tightly coupled" baseline
effort measurement, contrasted with the CryptoProvider-based version's zero
code edits.
"""
from __future__ import annotations

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class TightlyCoupledMessageService:
    def __init__(self):
        self._sk = ec.generate_private_key(ec.SECP256R1())  # <-- hard-wired algorithm choice #1
        self._pk = self._sk.public_key()

    def issue_identity(self):
        return self._sk, self._pk

    def sign_request(self, sk, message: bytes) -> bytes:
        return sk.sign(message, ec.ECDSA(hashes.SHA256()))  # <-- hard-wired algorithm choice #2

    def verify_request(self, pk, message: bytes, signature: bytes) -> bool:
        try:
            pk.verify(signature, message, ec.ECDSA(hashes.SHA256()))  # <-- hard-wired algorithm choice #3
            return True
        except Exception:
            return False

    @property
    def algorithm_name(self) -> str:
        return "ECDSA-P256"  # <-- hard-wired algorithm choice #4 (label itself must be edited too)

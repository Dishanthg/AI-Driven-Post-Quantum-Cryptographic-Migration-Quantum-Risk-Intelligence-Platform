"""Crypto-agility demonstration (design doc Section 65 / Experiment 6).

`SecureMessageService` is a tiny sample "Secure API" whose business logic -
sign a request, verify a response - depends ONLY on the `CryptoProvider`
interface (app.crypto.providers), never on a concrete library. Which
algorithm it uses is entirely determined by `config.yaml`'s `provider_key`.

This is the concrete artifact Experiment 6 measures: switching the algorithm
from ECDSA-P256 -> ML-DSA-65 -> SLH-DSA-SHA2-128F requires editing exactly one
YAML value and zero lines in this file (see
research/experiments/exp6_crypto_agility.py, which asserts that by hashing
this file's contents before and after each swap).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.crypto.providers import KeyPair, get_provider

CONFIG_PATH = Path(__file__).parent / "config.yaml"


class SecureMessageService:
    """Business logic never imports a cryptography library directly - only
    this class's own interface, which is itself only a thin pass-through to
    whatever CryptoProvider the configuration selects."""

    def __init__(self, provider_key: str):
        self._provider = get_provider(provider_key)
        if not self._provider.supports_sign:
            raise ValueError(f"provider {provider_key!r} does not support signing; SecureMessageService needs a signature-capable provider")

    @classmethod
    def from_config(cls, config_path: Path = CONFIG_PATH) -> "SecureMessageService":
        cfg = yaml.safe_load(config_path.read_text())
        return cls(cfg["provider_key"])

    def issue_identity(self) -> KeyPair:
        return self._provider.generate_keypair()

    def sign_request(self, identity: KeyPair, message: bytes) -> bytes:
        return self._provider.sign(identity, message)

    def verify_request(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        return self._provider.verify(public_key, message, signature)

    @property
    def algorithm_name(self) -> str:
        return self._provider.name


def set_active_provider(provider_key: str, config_path: Path = CONFIG_PATH) -> None:
    """The only "migration" action: rewrite one YAML value. No business-logic
    file is touched."""
    config_path.write_text(f"# The ONLY thing that changes when the \"Secure API\" sample app switches\n"
                            f"# cryptographic algorithm. See secure_api.py and README.md.\n"
                            f"provider_key: {provider_key}\n")


if __name__ == "__main__":
    service = SecureMessageService.from_config()
    print(f"Active algorithm: {service.algorithm_name}")
    identity = service.issue_identity()
    message = b"quantumshield-agility-demo-request"
    sig = service.sign_request(identity, message)
    ok = service.verify_request(identity.public_key, message, sig)
    print(f"Sign/verify roundtrip: {'OK' if ok else 'FAILED'} (signature {len(sig)} bytes)")

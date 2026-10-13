"""Roundtrip correctness for every CryptoProvider, and a check that the sizes
hard-coded into AlgorithmRegistry actually match what the underlying library
reports at runtime (registry.py's docstring claims this test exists - it now
does)."""
from __future__ import annotations

import pytest

from app.crypto import registry as algo_registry
from app.crypto.providers import UnsupportedOperation, get_provider

KEM_PROVIDER_KEYS = ["rsa2048", "ecdh_p256", "dh2048", "ml_kem_512", "ml_kem_768", "ml_kem_1024", "hybrid_ecdh_mlkem768"]
SIG_PROVIDER_KEYS = ["rsa2048", "ecdsa_p256", "ml_dsa_44", "ml_dsa_65", "ml_dsa_87", "slh_dsa_sha2_128f"]


@pytest.mark.parametrize("provider_key", KEM_PROVIDER_KEYS)
def test_kem_roundtrip(provider_key):
    provider = get_provider(provider_key)
    assert provider.supports_kem
    kp = provider.generate_keypair()
    ct, ss1 = provider.encapsulate(kp.public_key)
    ss2 = provider.decapsulate(kp, ct)
    assert ss1 == ss2
    assert len(ss1) > 0


@pytest.mark.parametrize("provider_key", SIG_PROVIDER_KEYS)
def test_signature_roundtrip(provider_key):
    provider = get_provider(provider_key)
    assert provider.supports_sign
    kp = provider.generate_keypair()
    message = b"quantumshield test message"
    sig = provider.sign(kp, message)
    assert provider.verify(kp.public_key, message, sig)
    assert not provider.verify(kp.public_key, b"tampered message", sig)


def test_ecdsa_does_not_support_kem():
    provider = get_provider("ecdsa_p256")
    with pytest.raises(UnsupportedOperation):
        provider.encapsulate(b"anything")


def test_mlkem_does_not_support_signing():
    provider = get_provider("ml_kem_768")
    with pytest.raises(UnsupportedOperation):
        provider.sign(provider.generate_keypair(), b"msg")


@pytest.mark.parametrize("algorithm_id", ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024", "ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
def test_registry_public_key_size_matches_runtime(algorithm_id):
    spec = algo_registry.get(algorithm_id)
    provider = get_provider(spec.provider_key)
    kp = provider.generate_keypair()
    assert spec.typical_key_size_bits == len(kp.public_key) * 8, (
        f"{algorithm_id}: registry claims {spec.typical_key_size_bits} bits "
        f"but provider produced a {len(kp.public_key) * 8}-bit public key"
    )


def test_hybrid_provider_combines_both_components():
    hybrid = get_provider("hybrid_ecdh_mlkem768")
    classical_only = get_provider("ecdh_p256")
    pqc_only = get_provider("ml_kem_768")

    kp = hybrid.generate_keypair()
    # hybrid public key must be strictly larger than either component alone (it embeds both)
    assert len(kp.public_key) > len(classical_only.generate_keypair().public_key)
    assert len(kp.public_key) > len(pqc_only.generate_keypair().public_key)

    ct, ss = hybrid.encapsulate(kp.public_key)
    ss2 = hybrid.decapsulate(kp, ct)
    assert ss == ss2

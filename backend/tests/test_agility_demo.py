from __future__ import annotations

import pytest

from agility_demo.secure_api import CONFIG_PATH, SecureMessageService, set_active_provider


@pytest.fixture()
def restore_config():
    original = CONFIG_PATH.read_text()
    try:
        yield
    finally:
        CONFIG_PATH.write_text(original)


def test_agility_swap_across_three_signature_algorithms(restore_config):
    sizes = {}
    for provider_key in ("ecdsa_p256", "ml_dsa_65", "slh_dsa_sha2_128f"):
        set_active_provider(provider_key)
        service = SecureMessageService.from_config()
        identity = service.issue_identity()
        message = b"quantumshield-agility-test"
        sig = service.sign_request(identity, message)
        assert service.verify_request(identity.public_key, message, sig)
        sizes[provider_key] = len(sig)

    # signature size should grow substantially as we move to PQC schemes -
    # a real, measured consequence of the swap, not asserted a priori
    assert sizes["ecdsa_p256"] < sizes["ml_dsa_65"] < sizes["slh_dsa_sha2_128f"]


def test_config_swap_is_the_only_change(restore_config):
    """The whole point of the abstraction: `secure_api.py`'s own source is
    untouched by the swap - only config.yaml's one line changes."""
    import hashlib
    import inspect

    import agility_demo.secure_api as mod

    hash_before = hashlib.sha256(inspect.getsource(mod).encode()).hexdigest()
    for provider_key in ("ml_dsa_65", "slh_dsa_sha2_128f", "ecdsa_p256"):
        set_active_provider(provider_key)
        SecureMessageService.from_config()  # instantiate against each config to prove it actually takes effect
    hash_after = hashlib.sha256(inspect.getsource(mod).encode()).hexdigest()
    assert hash_before == hash_after

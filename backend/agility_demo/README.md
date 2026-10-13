# Crypto-Agility Demo

Design doc Section 65 / Experiment 6.

`secure_api.py` is a minimal "Secure API" whose business logic (issue an
identity, sign a request, verify a request) depends only on
`app.crypto.providers.CryptoProvider`. `config.yaml` names the active
algorithm via `provider_key`.

**Run the demo through three algorithm generations:**

```
python -m agility_demo.secure_api                 # ECDSA-P256 (config.yaml default)
python -c "from agility_demo.secure_api import set_active_provider; set_active_provider('ml_dsa_65')"
python -m agility_demo.secure_api                 # ML-DSA-65 - same file, zero code changes
python -c "from agility_demo.secure_api import set_active_provider; set_active_provider('slh_dsa_sha2_128f')"
python -m agility_demo.secure_api                 # SLH-DSA-SHA2-128f - still zero code changes
```

`tightly_coupled_baseline.py` is a **comparison artifact only** (never
imported by the real service) showing what this file would look like without
the abstraction - four separate hard-wired algorithm references that would
each need editing to migrate.

`research/experiments/exp6_crypto_agility.py` runs both versions through this
exact swap sequence and records the measured comparison (files touched, lines
changed, code-diff size) as the Experiment 6 result - see
`research/tables/exp6_crypto_agility.md` after running it.

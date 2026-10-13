# Controlled Simulated Enterprise ("enterprise-lab")

Design doc Section 29 / Section 66. This is a **LAB / SYNTHETIC** environment,
not a real organization. Every file under `configs/` is a hand-authored (or,
for `internal-mesh.yaml`, seeded-and-generated) description of a fictional
service's cryptographic configuration - the same shape a real config-scan
would extract from TLS settings, application config, or certificate stores,
but entirely local and explicitly declared per project Rule ("only scan local
laboratory systems / explicitly configured test targets / imported
configuration files").

`app.discovery.scanner` reads every YAML file in this directory and imports it
into the `applications` / `assets` / `cryptographic_usage` tables - nothing is
inserted into the inventory that doesn't trace back to one of these files.

## Services

| File | Application | Business importance | Assets | Notable mix |
|---|---|---|---|---|
| `auth-service.yaml` | Authentication Service | critical | 4 | ECDSA/ECDH, session signing |
| `payment-service.yaml` | Payment Service | critical | 4 | RSA-2048 (legacy), AES-256 at rest |
| `customer-service.yaml` | Customer Service | high | 3 | ECDSA, AES-128 at rest |
| `api-gateway.yaml` | API Gateway | critical | 3 | RSA-3072 + ECDSA TLS termination |
| `database-tier.yaml` | Database Tier | high | 3 | TLS + AES-256 backups (10y retention) |
| `internal-ca.yaml` | Internal CA / PKI | critical | 3 | RSA-3072 root, ECDSA intermediate |
| `pqc-pilot.yaml` | PQC Pilot Program | medium | 4 | ML-KEM-768, ML-DSA-65, SLH-DSA, hybrid |
| `internal-mesh.yaml` (generated) | Internal Service Mesh | medium | 18 | seeded mixture, mostly mTLS |

Total: **42 assets** - within the Section 66 target range of 20-100.

## Regenerating the internal service mesh

```
python -m enterprise_lab.generate_mesh
```

Deterministic for a fixed `--seed` (default 42): documents the exact
per-algorithm sampling weights used, in the module docstring of
`generate_mesh.py`. This is SYNTHETIC LAB DATA, not real service inventory,
and is a separate generation process from `app.ai.dataset` (which generates
data to *train* the risk model, not to populate the inventory).

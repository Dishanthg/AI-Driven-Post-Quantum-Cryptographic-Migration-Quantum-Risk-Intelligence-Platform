# Cryptographic benchmark table

REAL BENCHMARK DATA — produced by `make benchmark` (app/benchmarks/run_all.py, 30 iterations/algorithm/operation) on the development machine this repository was built on. See research/tables/benchmark_sweep.csv for the raw values and docs/architecture (benchmark environment recording) for hardware/library versions.

| algorithm_id           | classification   | role         |   keygen_mean_ms |   encapsulate_mean_ms |   decapsulate_mean_ms |   sign_mean_ms |   verify_mean_ms |   public_key_bytes |   ciphertext_bytes |   signature_bytes |
|:-----------------------|:-----------------|:-------------|-----------------:|----------------------:|----------------------:|---------------:|-----------------:|-------------------:|-------------------:|------------------:|
| RSA-2048               | classical_pk     | public_key   |         200.1416 |                0.3295 |                3.0204 |         3.0884 |           0.3472 |                294 |           256.0000 |          256.0000 |
| RSA-3072               | classical_pk     | public_key   |         754.7344 |                0.5049 |               10.0348 |         9.5680 |           0.5358 |                422 |           384.0000 |          384.0000 |
| ECDSA-P256             | classical_pk     | signature    |           0.1845 |              nan      |              nan      |         0.1781 |           0.5242 |                 91 |           nan      |           70.0000 |
| ECDH-P256              | classical_pk     | key_exchange |           0.1725 |                0.6329 |                0.4067 |       nan      |         nan      |                 91 |            91.0000 |          nan      |
| DH-2048                | classical_pk     | key_exchange |           1.9222 |                3.3793 |                1.5805 |       nan      |         nan      |                552 |           553.0000 |          nan      |
| ML-KEM-512             | pqc_kem          | key_exchange |           0.0980 |                0.1545 |                0.2080 |       nan      |         nan      |                800 |           768.0000 |          nan      |
| ML-KEM-768             | pqc_kem          | key_exchange |           0.2180 |                0.2518 |                0.3091 |       nan      |         nan      |               1184 |          1088.0000 |          nan      |
| ML-KEM-1024            | pqc_kem          | key_exchange |           0.2365 |                0.3406 |                0.4431 |       nan      |         nan      |               1568 |          1568.0000 |          nan      |
| ML-DSA-44              | pqc_sig          | signature    |           0.4694 |              nan      |              nan      |        20.5422 |           0.4147 |               1312 |           nan      |         2420.0000 |
| ML-DSA-65              | pqc_sig          | signature    |           0.6133 |              nan      |              nan      |        27.3395 |           0.6224 |               1952 |           nan      |         3309.0000 |
| ML-DSA-87              | pqc_sig          | signature    |           0.9923 |              nan      |              nan      |        40.5555 |           0.9726 |               2592 |           nan      |         4627.0000 |
| SLH-DSA-SHA2-128F      | pqc_sig          | signature    |           2.0267 |              nan      |              nan      |        39.3957 |           2.6595 |                 32 |           nan      |        17088.0000 |
| HYBRID-ECDH-ML-KEM-768 | hybrid           | key_exchange |           0.3675 |                1.0067 |                1.1893 |       nan      |         nan      |               1279 |          1183.0000 |          nan      |

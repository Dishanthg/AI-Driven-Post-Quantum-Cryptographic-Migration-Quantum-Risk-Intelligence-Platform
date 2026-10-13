"""Seed reference data that is not organizational (i.e. not asset inventory):
the Algorithm table, mirrored 1:1 from the AlgorithmRegistry (design doc
Section 9 - the registry is the single source of truth; this just makes it
queryable/joinable from the relational schema).

Run via: python -m app.db.seed
"""
from __future__ import annotations

from app.crypto import registry as algo_registry
from app.db.base import Base
from app.db.models import Algorithm
from app.db.session import SessionLocal, engine


def seed_algorithms(db) -> int:
    count = 0
    for spec in algo_registry.all_specs():
        existing = db.get(Algorithm, spec.id)
        if existing is not None:
            continue
        db.add(Algorithm(
            id=spec.id,
            name=spec.name,
            family=spec.family,
            role=spec.role,
            classification=spec.classification,
            security_basis=spec.security_basis,
            quantum_vulnerability=spec.quantum_vulnerability,
            standard_ref=spec.standard_ref,
            library_source=spec.library_source,
            typical_key_size_bits=spec.typical_key_size_bits,
        ))
        count += 1
    db.commit()
    return count


def main() -> None:
    Base.metadata.create_all(bind=engine)  # no-op if alembic already applied; safety net for fresh dev DBs
    db = SessionLocal()
    try:
        n = seed_algorithms(db)
        print(f"Seeded {n} new algorithm(s); {len(algo_registry.all_specs())} total in registry.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

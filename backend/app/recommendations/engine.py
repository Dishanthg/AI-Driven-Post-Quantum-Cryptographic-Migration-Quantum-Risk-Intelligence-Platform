"""PQC Recommendation Engine (design doc Section 24).

Deterministic, rule-based, and fully explained - given an asset's current
algorithm, its most recent risk assessment, its migration complexity, and
(where available) REAL measured benchmark data for candidate target
algorithms, this produces one of five strategies:

  pqc_migration    - move directly to a standardized PQC algorithm
  hybrid_migration  - transitional classical+PQC composition (only available
                      for key-exchange-shaped usage, where HybridKEMProvider
                      exists; design doc Section 25)
  deferred          - not yet a priority, or not applicable (symmetric/hash
                      algorithms, where Grover only halves the security
                      margin - Rule 7/Section 10)
  agility_prep      - medium-priority assets: recommend adopting the
                      CryptoProvider abstraction now so a later algorithm swap
                      is a config change, without migrating yet
  manual_review     - ambiguous cases the rules can't confidently resolve
                      (e.g. an already-PQC/hybrid asset with no clear next step)

No ML is used here: the recommendation is a transparent function of the risk
priority (already produced by the AI risk engine upstream) and the asset's
own attributes, so its reasoning is directly inspectable (Section 24: "explain
why, what trade-offs, what assumptions").

Assets already on a PQC or hybrid algorithm are skipped (nothing to
recommend).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.crypto import registry as algo_registry
from app.crypto.registry import HASH, HYBRID, PQC_KEM, PQC_SIG
from app.db.models import Algorithm, Asset, Benchmark, BenchmarkRun, PQCRecommendation, RiskAssessment

STRATEGY_PQC = "pqc_migration"
STRATEGY_HYBRID = "hybrid_migration"
STRATEGY_DEFERRED = "deferred"
STRATEGY_AGILITY_PREP = "agility_prep"
STRATEGY_MANUAL_REVIEW = "manual_review"

LONG_LIVED_YEARS_THRESHOLD = 10  # data/trust anchors living longer than this get the conservative hash-based signature choice

# TLS handshake fragmentation is a documented, real concern for very large PQC
# signatures in certificate chains (e.g. SLH-DSA's ~17KB signature vs. a single
# TCP initial-window-friendly ~8KB budget) - see e.g. IETF/Cloudflare discussion
# of PQC certificate-chain size in TLS 1.3. This threshold is an engineering
# judgment call grounded in that real, documented concern, not an arbitrary
# tuning knob chosen to make any particular algorithm look good.
TLS_HANDSHAKE_SIGNATURE_BUDGET_BYTES = 8000


def _real_benchmarked_signature_bytes(db: Session | None, algorithm_id: str) -> int | None:
    """REAL BENCHMARK DATA lookup (never a static spec constant): the most
    recent completed 'sign' BenchmarkRun's measured signature size for this
    algorithm, if one has actually been run. Returns None (not a fabricated
    fallback value) if db is None or no such benchmark has been executed yet
    - callers must degrade to the lifetime-only heuristic in that case."""
    if db is None:
        return None
    row = (
        db.query(BenchmarkRun)
        .join(Benchmark, Benchmark.id == BenchmarkRun.benchmark_id)
        .filter(Benchmark.algorithm_id == algorithm_id, Benchmark.operation == "sign", BenchmarkRun.status == "completed")
        .order_by(BenchmarkRun.completed_at.desc())
        .first()
    )
    if row is None:
        return None
    return row.summary_stats_json.get("ciphertext_or_signature_bytes")


@dataclass
class RecommendationDecision:
    strategy: str
    target_algorithm_id: str | None
    rationale: str
    assumptions: str
    tradeoffs: str


def _target_for_signature(
    data_lifetime_years: int, db: Session | None = None, usage_type: str | None = None, internet_exposure: bool = False
) -> tuple[str, str]:
    if data_lifetime_years > LONG_LIVED_YEARS_THRESHOLD:
        slh_dsa_bytes = _real_benchmarked_signature_bytes(db, "SLH-DSA-SHA2-128F")
        handshake_sensitive = usage_type == "tls_certificate" and internet_exposure
        if handshake_sensitive and slh_dsa_bytes is not None and slh_dsa_bytes > TLS_HANDSHAKE_SIGNATURE_BUDGET_BYTES:
            return "ML-DSA-65", (
                "Data/trust-anchor lifetime exceeds "
                f"{LONG_LIVED_YEARS_THRESHOLD} years, which would normally favor SLH-DSA's conservative "
                f"hash-based security assumption, but this asset is an internet-facing TLS certificate and "
                f"SLH-DSA-SHA2-128F's REAL measured signature size ({slh_dsa_bytes} bytes, from this "
                f"platform's own benchmark run) exceeds the "
                f"{TLS_HANDSHAKE_SIGNATURE_BUDGET_BYTES}-byte handshake budget past which certificate-chain "
                "TCP fragmentation becomes a practical concern; ML-DSA-65 is recommended instead despite the "
                "less conservative (lattice-based, not purely hash-based) security assumption."
            )
        return "SLH-DSA-SHA2-128F", (
            "Data/trust-anchor lifetime exceeds "
            f"{LONG_LIVED_YEARS_THRESHOLD} years; SLH-DSA is a hash-based signature whose security "
            "rests only on hash-function assumptions, a more conservative choice for long-lived trust "
            "anchors than a lattice-based scheme, at the cost of larger signatures and slower signing."
            + ("" if not handshake_sensitive else " (No real benchmark data was available to check this "
               "asset's TLS handshake signature-size budget; run `make benchmark` for a performance-aware "
               "recommendation.)")
        )
    return "ML-DSA-65", "ML-DSA-65 (NIST security category 3) balances signature/key size against a comfortable security margin for a typical signing lifetime."


def decide(asset: Asset, algorithm: Algorithm, risk: RiskAssessment, db: Session | None = None) -> RecommendationDecision:
    spec = algo_registry.get(algorithm.id)

    if spec.classification in (PQC_KEM, PQC_SIG, HYBRID):
        return RecommendationDecision(
            strategy=STRATEGY_MANUAL_REVIEW,
            target_algorithm_id=None,
            rationale="Asset already uses a standardized PQC or hybrid algorithm; no further migration is needed.",
            assumptions="Assumes the current PQC algorithm choice remains standards-compliant.",
            tradeoffs="None - flagged for periodic manual review only, e.g. if the standard is later revised.",
        )

    if spec.classification == HASH or spec.role == "symmetric":
        rationale = (
            "Grover's algorithm provides only a quadratic (not exponential) speedup against symmetric/hash "
            "primitives (Rule 7); this is not a public-key algorithm requiring PQC replacement."
        )
        if algorithm.typical_key_size_bits < 256 and spec.role == "symmetric":
            rationale += (
                f" Current key size ({algorithm.typical_key_size_bits} bits) provides a reduced post-quantum "
                "security margin (~half under Grover); consider upgrading to a 256-bit key when convenient."
            )
        return RecommendationDecision(
            strategy=STRATEGY_DEFERRED,
            target_algorithm_id=None,
            rationale=rationale,
            assumptions="Assumes Grover's algorithm remains the best known quantum attack against this primitive class.",
            tradeoffs="No migration cost incurred now; residual risk is the (bounded, quadratic) margin reduction.",
        )

    # remaining case: classical public-key algorithm (RSA/ECC/DH) - genuinely quantum_vulnerable
    priority = risk.priority
    is_signature_like = spec.role == "signature" or asset.usage_type == "signing"

    if priority == "critical":
        if is_signature_like:
            target, why = _target_for_signature(asset.data_lifetime_years, db, asset.usage_type, asset.internet_exposure)
            return RecommendationDecision(
                strategy=STRATEGY_PQC,
                target_algorithm_id=target,
                rationale=(
                    f"Critical-priority asset (risk score {risk.risk_score:.2f}) on a quantum-vulnerable "
                    f"signature algorithm ({algorithm.name}); direct migration recommended given the urgency. {why}"
                ),
                assumptions="Assumes downstream verifiers can be updated to support the new signature algorithm in the same change window.",
                tradeoffs="Larger signature/public-key sizes than the classical algorithm; requires coordinated verifier-side rollout.",
            )

        if asset.migration_complexity == "high":
            return RecommendationDecision(
                strategy=STRATEGY_HYBRID,
                target_algorithm_id="HYBRID-ECDH-ML-KEM-768",
                rationale=(
                    f"Critical-priority asset (risk score {risk.risk_score:.2f}) but high migration complexity; "
                    "a hybrid classical+PQC key exchange gives immediate quantum-resistant protection of the "
                    "shared secret while preserving compatibility with the existing classical stack during a "
                    "longer migration window."
                ),
                assumptions="Assumes both peers can be upgraded to support the hybrid TLS key-exchange extension.",
                tradeoffs="Pays both the classical and PQC computational/bandwidth cost simultaneously; security holds if either component is secure, but this is not a proof of additive security.",
            )
        return RecommendationDecision(
            strategy=STRATEGY_PQC,
            target_algorithm_id="ML-KEM-768",
            rationale=(
                f"Critical-priority asset (risk score {risk.risk_score:.2f}) on a quantum-vulnerable "
                f"key-exchange/public-key algorithm ({algorithm.name}) with low/medium migration complexity; "
                "direct migration to ML-KEM-768 is recommended."
            ),
            assumptions="Assumes the peer/client population can be upgraded to negotiate ML-KEM.",
            tradeoffs="Larger public key and ciphertext than classical ECDH; requires protocol version negotiation.",
        )

    if priority == "high":
        if is_signature_like and asset.migration_complexity != "high":
            target, why = _target_for_signature(asset.data_lifetime_years, db, asset.usage_type, asset.internet_exposure)
            return RecommendationDecision(
                strategy=STRATEGY_PQC,
                target_algorithm_id=target,
                rationale=f"High-priority signature-role asset with manageable migration complexity. {why}",
                assumptions="Assumes downstream verifiers can be updated within the planning window.",
                tradeoffs="Larger signature/public-key sizes than the classical algorithm.",
            )
        if not is_signature_like:
            return RecommendationDecision(
                strategy=STRATEGY_HYBRID,
                target_algorithm_id="HYBRID-ECDH-ML-KEM-768",
                rationale="High-priority key-exchange-shaped asset; hybrid migration reduces risk now without requiring a full compatibility cutover.",
                assumptions="Assumes both peers can be upgraded to support the hybrid TLS key-exchange extension.",
                tradeoffs="Both classical and PQC computational/bandwidth cost paid simultaneously.",
            )
        return RecommendationDecision(
            strategy=STRATEGY_DEFERRED,
            target_algorithm_id=None,
            rationale="High-priority signature-role asset with high migration complexity; deferred pending a dedicated migration project rather than an ad hoc change.",
            assumptions="Assumes risk does not materially worsen before the dedicated migration project begins.",
            tradeoffs="Residual quantum-vulnerable exposure persists until the dedicated project executes.",
        )

    if priority == "medium":
        return RecommendationDecision(
            strategy=STRATEGY_AGILITY_PREP,
            target_algorithm_id=None,
            rationale=(
                "Medium-priority asset: recommend adopting the CryptoProvider abstraction now (Section 28) so "
                "that a future algorithm swap is a configuration change rather than a code change, deferring the "
                "actual cryptographic migration until priority increases or a convenient maintenance window arises."
            ),
            assumptions="Assumes the asset's owning application can absorb a refactor to the provider abstraction without a full migration yet.",
            tradeoffs="Refactoring effort now, in exchange for lower-cost migration later; no immediate quantum-risk reduction.",
        )

    return RecommendationDecision(
        strategy=STRATEGY_DEFERRED,
        target_algorithm_id=None,
        rationale=f"Low-priority asset (risk score {risk.risk_score:.2f}); no near-term action recommended.",
        assumptions="Assumes the asset's risk profile (criticality/sensitivity/exposure) does not change materially.",
        tradeoffs="Residual quantum-vulnerable exposure persists, judged acceptable given current low priority.",
    )


def recommend_for_asset(db: Session, asset: Asset) -> PQCRecommendation | None:
    algorithm = db.get(Algorithm, asset.algorithm_id)
    if algorithm is None:
        return None
    latest_risk = (
        db.query(RiskAssessment)
        .filter_by(asset_id=asset.id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    if latest_risk is None:
        return None

    decision = decide(asset, algorithm, latest_risk, db)
    rec = PQCRecommendation(
        asset_id=asset.id,
        risk_assessment_id=latest_risk.id,
        strategy=decision.strategy,
        target_algorithm_id=decision.target_algorithm_id,
        rationale=decision.rationale,
        assumptions=decision.assumptions,
        tradeoffs=decision.tradeoffs,
    )
    db.add(rec)
    return rec


def recommend_for_all_assets(db: Session) -> list[PQCRecommendation]:
    recs = []
    for asset in db.query(Asset).all():
        rec = recommend_for_asset(db, asset)
        if rec is not None:
            recs.append(rec)
    db.commit()
    return recs


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        recs = recommend_for_all_assets(session)
        by_strategy: dict[str, int] = {}
        for r in recs:
            by_strategy[r.strategy] = by_strategy.get(r.strategy, 0) + 1
        print(f"Generated {len(recs)} recommendations. Strategy distribution: {by_strategy}")
    finally:
        session.close()

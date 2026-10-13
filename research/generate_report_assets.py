"""Generates research/figures/*.png and research/tables/*.md from artifacts that
were actually produced by prior runs (research/tables/benchmark_sweep.csv from
`make benchmark`, and the latest risk-model metadata.json from `make train`).

This script performs NO simulation and NO synthetic value generation of its
own - it only reads persisted results and renders/tabulates them. If an input
artifact is missing, the corresponding figure/table is skipped and reported
as NOT GENERATED rather than fabricated.

Run: python -m research.generate_report_assets   (from repo root, with .venv active)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = REPO_ROOT / "research" / "tables"
FIGURES_DIR = REPO_ROOT / "research" / "figures"
MODELS_DIR = REPO_ROOT / "backend" / "artifacts" / "models" / "risk_prioritization"

SKIPPED: list[str] = []


def _latest_model_metadata() -> dict | None:
    if not MODELS_DIR.exists():
        return None
    versions = sorted((p for p in MODELS_DIR.iterdir() if p.is_dir()), key=lambda p: p.name)
    if not versions:
        return None
    meta_path = versions[-1] / "metadata.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text()), versions[-1].name


def fig_keygen_classical_vs_pqc(df: pd.DataFrame) -> None:
    d = df.dropna(subset=["keygen_mean_ms"]).copy()
    d = d.sort_values("keygen_mean_ms")
    colors = d["classification"].map({
        "classical_pk": "#6b7280", "pqc_kem": "#2563eb", "pqc_sig": "#7c3aed", "hybrid": "#059669",
    }).fillna("#9ca3af")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(d["algorithm_id"], d["keygen_mean_ms"], color=colors)
    ax.set_xlabel("Key generation, mean ms (log scale) — n=30 iterations/algorithm")
    ax.set_xscale("log")
    ax.set_title("Key generation time: classical vs. standardized PQC vs. hybrid\n"
                  "REAL BENCHMARK DATA — executed on this machine (see research/tables/)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "keygen_classical_vs_pqc.png", dpi=150)
    plt.close(fig)


def fig_key_and_artifact_sizes(df: pd.DataFrame) -> None:
    d = df.copy()
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, col, title in zip(
        axes,
        ["public_key_bytes", "ciphertext_bytes", "signature_bytes"],
        ["Public key size (bytes)", "KEM ciphertext size (bytes)", "Signature size (bytes)"],
    ):
        sub = d.dropna(subset=[col]).sort_values(col)
        if sub.empty:
            ax.set_title(f"{title}\n(no algorithms with this artifact)")
            continue
        colors = sub["classification"].map({
            "classical_pk": "#6b7280", "pqc_kem": "#2563eb", "pqc_sig": "#7c3aed", "hybrid": "#059669",
        }).fillna("#9ca3af")
        ax.barh(sub["algorithm_id"], sub[col], color=colors)
        ax.set_title(title)
    fig.suptitle("Artifact sizes — REAL BENCHMARK DATA (research/tables/benchmark_sweep.csv)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "artifact_sizes.png", dpi=150)
    plt.close(fig)


def fig_sign_verify(df: pd.DataFrame) -> None:
    d = df.dropna(subset=["sign_mean_ms"]).sort_values("sign_mean_ms")
    if d.empty:
        SKIPPED.append("fig_sign_verify: no signature rows in benchmark_sweep.csv")
        return
    x = range(len(d))
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.38
    ax.bar([i - width / 2 for i in x], d["sign_mean_ms"], width, label="sign", color="#7c3aed")
    ax.bar([i + width / 2 for i in x], d["verify_mean_ms"], width, label="verify", color="#a78bfa")
    ax.set_xticks(list(x))
    ax.set_xticklabels(d["algorithm_id"], rotation=30, ha="right")
    ax.set_ylabel("mean ms (log scale)")
    ax.set_yscale("log")
    ax.legend()
    ax.set_title("Sign/verify cost, classical vs. PQC signatures — REAL BENCHMARK DATA")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "sign_verify_cost.png", dpi=150)
    plt.close(fig)


def fig_model_comparison(meta: dict) -> None:
    metrics = meta["metrics"]
    models = [k for k in ("rule_baseline", "logistic_regression", "random_forest", "xgboost") if k in metrics]
    macro_f1 = [metrics[m]["macro_f1"] for m in models]
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ["#9ca3af" if m == "rule_baseline" else "#2563eb" for m in models]
    bars = ax.bar([m.replace("_", " ") for m in models], macro_f1, color=colors)
    for b, v in zip(bars, macro_f1):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Macro-F1 on held-out test split (n_test=%d)" % meta.get("n_test", 0))
    ax.set_title(
        "AI risk prioritization vs. rule baseline\n"
        f"SYNTHETIC DATA ({meta.get('dataset_ref')}) — REAL, EXECUTED TRAINING RUN (seed={meta.get('random_seed')})"
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "risk_model_comparison.png", dpi=150)
    plt.close(fig)


def fig_ranking_consistency(meta: dict) -> None:
    rc = meta["metrics"].get("ranking_consistency")
    if not rc:
        SKIPPED.append("fig_ranking_consistency: no ranking_consistency block in model metadata")
        return
    labels = ["Rule baseline\n(self-consistency)", "ML (RandomForest)\nfold-pairwise", "ML vs. rule\nagreement"]
    values = [
        rc["rule_baseline_fold_pairwise_kendall_tau"],
        rc["ml_fold_pairwise_kendall_tau_mean"],
        rc["ml_vs_rule_kendall_tau"],
    ]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(labels, values, color=["#9ca3af", "#2563eb", "#f59e0b"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Kendall's tau")
    ax.set_title("H1: ranking consistency, rule baseline vs. ML\nSYNTHETIC DATA — REAL, EXECUTED RUN")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "ranking_consistency.png", dpi=150)
    plt.close(fig)


def table_benchmark_markdown(df: pd.DataFrame) -> None:
    cols = ["algorithm_id", "classification", "role", "keygen_mean_ms", "encapsulate_mean_ms",
            "decapsulate_mean_ms", "sign_mean_ms", "verify_mean_ms", "public_key_bytes",
            "ciphertext_bytes", "signature_bytes"]
    d = df[[c for c in cols if c in df.columns]].copy()
    header = (
        "# Cryptographic benchmark table\n\n"
        "REAL BENCHMARK DATA — produced by `make benchmark` "
        "(app/benchmarks/run_all.py, 30 iterations/algorithm/operation) on the "
        "development machine this repository was built on. See "
        "research/tables/benchmark_sweep.csv for the raw values and "
        "docs/architecture (benchmark environment recording) for hardware/"
        "library versions.\n\n"
    )
    md = header + d.to_markdown(index=False, floatfmt=".4f")
    (TABLES_DIR / "benchmark_comparison.md").write_text(md + "\n")


def table_risk_model_markdown(meta: dict) -> None:
    metrics = meta["metrics"]
    rows = []
    for name in ("rule_baseline", "logistic_regression", "random_forest", "xgboost"):
        if name not in metrics:
            continue
        m = metrics[name]
        rows.append({
            "model": name,
            "macro_f1": round(m["macro_f1"], 4),
            "macro_precision": round(m["macro_precision"], 4),
            "macro_recall": round(m["macro_recall"], 4),
            "quadratic_weighted_kappa": round(m["quadratic_weighted_kappa"], 4),
            "train_seconds": round(m.get("train_seconds", 0.0), 4) if "train_seconds" in m else "n/a (deterministic rule, not trained)",
        })
    df = pd.DataFrame(rows)
    header = (
        "# AI risk prioritization: model comparison table\n\n"
        f"SYNTHETIC DATA ({meta.get('dataset_ref')}), REAL EXECUTED TRAINING RUN. "
        f"Model version: {meta.get('version')}. Random seed: {meta.get('random_seed')}. "
        f"n_train={meta.get('n_train')}, n_test={meta.get('n_test')}.\n\n"
    )
    md = header + df.to_markdown(index=False)
    (TABLES_DIR / "risk_model_comparison.md").write_text(md + "\n")


def main() -> int:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    bench_csv = TABLES_DIR / "benchmark_sweep.csv"
    if bench_csv.exists():
        df = pd.read_csv(bench_csv)
        fig_keygen_classical_vs_pqc(df)
        fig_key_and_artifact_sizes(df)
        fig_sign_verify(df)
        table_benchmark_markdown(df)
        print(f"Generated benchmark figures/tables from {bench_csv} ({len(df)} algorithms).")
    else:
        SKIPPED.append(f"benchmark figures/tables: {bench_csv} not found — run `make benchmark` first")

    model_result = _latest_model_metadata()
    if model_result:
        meta, version = model_result
        fig_model_comparison(meta)
        fig_ranking_consistency(meta)
        table_risk_model_markdown(meta)
        print(f"Generated risk-model figures/tables from artifact version {version}.")
    else:
        SKIPPED.append(f"risk-model figures/tables: no metadata.json under {MODELS_DIR} — run `make train` first")

    if SKIPPED:
        print("\nNOT GENERATED (missing prerequisite artifacts):")
        for s in SKIPPED:
            print(f"  - {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

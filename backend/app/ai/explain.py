"""SHAP-based explainability for the trained risk model (design doc Section 22).

Loads the currently active model artifact (produced by app/ai/train.py) and
returns real SHAP values for a given feature vector - never a hand-authored
"top factors" list for the ML path (the rule baseline's equivalent explanation
is its own transparent weight breakdown, see rule_baseline.assess).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from app.core.config import get_settings


class RiskExplainer:
    def __init__(self, artifact_dir: Path):
        bundle = joblib.load(artifact_dir / "model.joblib")
        self.model = bundle["model"]
        self.scaler = bundle["scaler"]
        self.label_order = bundle["label_order"]
        self.feature_cols = bundle["feature_cols"]
        metadata = json.loads((artifact_dir / "metadata.json").read_text())
        self.version = metadata["version"]
        self.algorithm = metadata["algorithm"]

        if isinstance(self.model, RandomForestClassifier | XGBClassifier):
            self._explainer = shap.TreeExplainer(self.model)
            self._needs_scaling = False
        elif isinstance(self.model, LogisticRegression):
            self._explainer = None  # uses coefficient-based contribution, computed directly (still real, not fabricated)
            self._needs_scaling = True
        else:
            raise TypeError(f"No SHAP strategy configured for model type {type(self.model)}")

    def predict_and_explain(self, feature_vector: list[float]) -> dict:
        x = pd.DataFrame([feature_vector], columns=self.feature_cols)
        x_model = self.scaler.transform(x) if self._needs_scaling and self.scaler is not None else x.to_numpy()

        proba = self.model.predict_proba(x_model)[0]
        pred_idx = int(np.argmax(proba))
        priority = self.label_order[pred_idx]
        confidence = float(proba[pred_idx])
        risk_score = float(proba @ np.arange(len(self.label_order)) / (len(self.label_order) - 1))

        if self._explainer is not None:
            shap_values = self._explainer.shap_values(x_model)
            # shap_values: list[n_classes] of (1, n_features) for older API, or (1, n_features, n_classes) for newer
            arr = np.array(shap_values)
            contrib = arr[0, :, pred_idx] if arr.ndim == 3 else arr[pred_idx][0]
        else:
            coefs = self.model.coef_[pred_idx] if self.model.coef_.shape[0] > 1 else self.model.coef_[0]
            contrib = coefs * x_model[0]

        factors = sorted(zip(self.feature_cols, contrib.tolist(), strict=True), key=lambda kv: -abs(kv[1]))
        return {
            "method": "ml_model",
            "model_algorithm": self.algorithm,
            "model_version": self.version,
            "risk_score": risk_score,
            "priority": priority,
            "confidence": confidence,
            "top_factors": factors[:3],
            "all_factors": factors,
        }


def load_active_explainer() -> RiskExplainer:
    settings = get_settings()
    base = settings.model_registry_dir / "risk_prioritization"
    if not base.exists():
        raise FileNotFoundError("No trained risk model found. Run: python -m app.ai.train")
    versions = sorted(base.iterdir())
    if not versions:
        raise FileNotFoundError("No trained risk model versions found.")
    latest = versions[-1]
    return RiskExplainer(latest)

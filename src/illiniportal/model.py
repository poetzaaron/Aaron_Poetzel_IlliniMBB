"""The translation model: one interpretable ridge regression per metric."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import features

_ALPHAS = np.logspace(-3, 3, 25)


def _make_pipeline() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("ridge", RidgeCV(alphas=_ALPHAS)),
    ])


class TranslationModel:
    """Fits/serves a ridge model per metric; keeps coefficients legible."""

    def __init__(self, metrics: list[str] | None = None):
        self.metrics = metrics
        self.models: dict[str, Pipeline] = {}
        self.feature_names: dict[str, list[str]] = {}

    def fit(self, pairs: pd.DataFrame) -> "TranslationModel":
        metrics = self.metrics or features.usable_metrics(pairs)
        self.metrics = metrics
        for m in metrics:
            X, y, _ = features.build_design(pairs, m)
            pipe = _make_pipeline().fit(X, y)
            self.models[m] = pipe
            self.feature_names[m] = features.feature_columns(m)
        return self

    def predict(self, pairs: pd.DataFrame) -> pd.DataFrame:
        """Predicted post-transfer value per metric (NaN where data missing)."""
        out = pd.DataFrame(index=pairs.index)
        for m, pipe in self.models.items():
            df = pairs.copy()
            df[f"{m}_x_dL"] = df[f"{m}_pre"] * df[features.LEVEL]
            cols = self.feature_names[m]
            mask = df[cols].notna().all(axis=1)
            preds = np.full(len(df), np.nan)
            if mask.any():
                preds[mask.values] = pipe.predict(df.loc[mask, cols].to_numpy(float))
            out[f"{m}_proj"] = preds
        return out

    def coefficients(self) -> pd.DataFrame:
        """Standardised coefficients per metric: what a staff actually reads."""
        rows = []
        for m, pipe in self.models.items():
            ridge = pipe.named_steps["ridge"]
            for name, coef in zip(self.feature_names[m], ridge.coef_):
                rows.append({"metric": m, "feature": name, "coef_std": coef})
            rows.append({"metric": m, "feature": "_intercept",
                         "coef_std": ridge.intercept_})
            rows.append({"metric": m, "feature": "_alpha",
                         "coef_std": ridge.alpha_})
        return pd.DataFrame(rows)

    def save(self, path: Path) -> None:
        import joblib
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"metrics": self.metrics, "models": self.models,
             "feature_names": self.feature_names, "version": 1},
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "TranslationModel":
        import joblib
        blob = joblib.load(Path(path))
        obj = cls(metrics=blob["metrics"])
        obj.models = blob["models"]
        obj.feature_names = blob["feature_names"]
        return obj

"""Out-of-sample validation: model vs a naive ``post = pre`` baseline.

Temporal split (train on transfers landing in seasons <= cutoff, test on the
held-out later seasons) is the honest test of whether the model captures
*level-adjusted regression to the mean* rather than memorising.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import features
from .model import TranslationModel


def temporal_split(pairs: pd.DataFrame, cutoff: int = 2023):
    train = pairs[pairs["year_post"] <= cutoff].copy()
    test = pairs[pairs["year_post"] > cutoff].copy()
    return train, test


def _metrics(y_true, y_pred) -> dict:
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"mae": mae, "rmse": rmse, "r2": r2}


def evaluate(pairs: pd.DataFrame, cutoff: int = 2023) -> pd.DataFrame:
    """Per-metric out-of-sample table comparing the model to the naive baseline."""
    train, test = temporal_split(pairs, cutoff)
    metrics = features.usable_metrics(train)
    model = TranslationModel(metrics=metrics).fit(train)

    rows = []
    for m in metrics:
        _, y_te, df_te = features.build_design(test, m)
        if len(y_te) == 0:
            continue
        y_model = model.predict(df_te)[f"{m}_proj"].to_numpy(float)
        y_naive = df_te[f"{m}_pre"].to_numpy(float)

        mod = _metrics(y_te, y_model)
        nai = _metrics(y_te, y_naive)
        rows.append({
            "metric": m, "n_test": int(len(y_te)),
            "mae_model": mod["mae"], "mae_naive": nai["mae"],
            "rmse_model": mod["rmse"], "r2_model": mod["r2"], "r2_naive": nai["r2"],
            "mae_gain_%": 100.0 * (nai["mae"] - mod["mae"]) / nai["mae"]
            if nai["mae"] else float("nan"),
        })
    return pd.DataFrame(rows)

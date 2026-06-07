"""Assemble the per-metric design matrices for the translation model.

For each target metric ``m`` the model is

    m_post = b0 + b1*m_pre + b2*ΔL + b3*(m_pre*ΔL) + g'Z + e

with Z = [usage_pre, min_pct_pre, age_proxy, gp_pre]. ΔL (``delta_L``) is the
adjEM jump between destination and origin programs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

LEVEL = "delta_L"


def feature_columns(metric: str) -> list[str]:
    """Design-matrix columns for one metric (interaction term included).

    A control is dropped when it coincides with the metric's own ``_pre`` term
    (e.g. ``usage_pre`` for the usage model) to avoid a duplicate column.
    """
    inter = f"{metric}_x_dL"
    base = [f"{metric}_pre", LEVEL, inter]
    return base + [c for c in config.CONTROLS if c not in base]


def build_design(pairs: pd.DataFrame, metric: str):
    """Return (X, y, frame) for ``metric``, rows with complete data only."""
    pre, post = f"{metric}_pre", f"{metric}_post"
    df = pairs.copy()
    df[f"{metric}_x_dL"] = df[pre] * df[LEVEL]

    cols = feature_columns(metric)
    needed = cols + [post]
    df = df.dropna(subset=[c for c in needed if c in df.columns])

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"metric '{metric}' missing feature columns: {missing}")

    X = df[cols].to_numpy(dtype=float)
    y = df[post].to_numpy(dtype=float)
    return X, y, df


def usable_metrics(pairs: pd.DataFrame, min_rows: int = 30) -> list[str]:
    """Metrics with enough complete pre/post rows to model."""
    out = []
    for m in config.METRICS:
        if f"{m}_pre" in pairs.columns and f"{m}_post" in pairs.columns:
            n = pairs[[f"{m}_pre", f"{m}_post", LEVEL]].dropna().shape[0]
            if n >= min_rows:
                out.append(m)
    return out

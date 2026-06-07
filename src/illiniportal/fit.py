"""Transparent fit layer: projected production -> skills -> translation & fit.

Every component is visible by design; a black-box fit number is useless to a
coach, "fits because shooting + creation + experience" is the product.

- **translation score**: will this profile keep *producing* at the new level?
  A fixed-weight blend of projected skills (efficiency / role / playmaking /
  rebounding / ball-security / availability). Level-independent of team need.
- **fit score**: translation re-weighted by *Illinois's* need vector, plus an
  explicit experience bonus (Underwood's stated recipe: experienced portal
  players).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Skill = weighted blend of standardised projected metrics (sign-oriented so
# higher is always better; to_pct is a negative).
SKILLS = {
    "shooting":      [("ts", 1.0), ("efg", 0.5)],
    "shot_creation": [("usage", 1.0), ("ast_pct", 0.4)],
    "playmaking":    [("ast_pct", 1.0), ("to_pct", -0.4)],
    "ball_security": [("to_pct", -1.0)],
    "rebounding":    [("orb_pct", 0.5), ("drb_pct", 0.5)],
    "efficiency":    [("ortg", 0.5), ("ts", 0.5)],
    "availability":  [("min_pct", 1.0)],
}

# "Keeps producing at the new level"; team-agnostic.
TRANSLATION_WEIGHTS = {
    "efficiency": 0.30, "availability": 0.20, "shot_creation": 0.15,
    "playmaking": 0.15, "rebounding": 0.10, "ball_security": 0.10,
}

# Illinois 2026-27 need vector (DOCUMENTED ASSUMPTION; edit per staff input).
# Returning frontcourt (Ivisic brothers, Mirkovic) covers size/rebounding, so
# the need tilts to guard shooting, creation, and efficient experienced scoring.
NEED_WEIGHTS = {
    "shooting": 0.24, "shot_creation": 0.16, "playmaking": 0.18,
    "efficiency": 0.18, "ball_security": 0.10, "availability": 0.09,
    "rebounding": 0.05,
}

# Experience up-weighted per Underwood's stated philosophy (visible knob).
EXPERIENCE_WEIGHT = 0.25


def _z(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and sd > 0 else s * 0.0


def skill_frame(proj: pd.DataFrame) -> pd.DataFrame:
    """Standardised skill scores from projected metrics (z within the pool)."""
    zmetric = {m: _z(proj[m]) for m in proj.columns}
    skills = pd.DataFrame(index=proj.index)
    for skill, parts in SKILLS.items():
        total = pd.Series(0.0, index=proj.index)
        used = False
        for metric, w in parts:
            if metric in zmetric:
                total = total + w * zmetric[metric]
                used = True
        skills[skill] = total if used else 0.0
    return skills.apply(_z)  # re-standardise so skills are comparable


def _weighted(skills: pd.DataFrame, weights: dict) -> pd.Series:
    out = pd.Series(0.0, index=skills.index)
    for skill, w in weights.items():
        if skill in skills.columns:
            out = out + w * skills[skill]
    return out


def translation_score(skills: pd.DataFrame) -> pd.Series:
    return _weighted(skills, TRANSLATION_WEIGHTS)


def fit_score(skills: pd.DataFrame, age_proxy: pd.Series,
              need_weights: dict | None = None,
              experience_weight: float | None = None) -> pd.Series:
    """Need-weighted fit + experience bonus. Weights are overridable (UI)."""
    nw = need_weights if need_weights is not None else NEED_WEIGHTS
    ew = EXPERIENCE_WEIGHT if experience_weight is None else experience_weight
    return _weighted(skills, nw) + ew * _z(age_proxy)


def score_pool(proj: pd.DataFrame, meta: pd.DataFrame,
               need_weights: dict | None = None,
               experience_weight: float | None = None) -> pd.DataFrame:
    """Full scored board for a projected pool, with skill breakdown columns."""
    skills = skill_frame(proj)
    out = meta.reset_index(drop=True).copy()
    skills = skills.reset_index(drop=True)
    proj = proj.reset_index(drop=True)
    for m in proj.columns:
        out[f"proj_{m}"] = proj[m].values
    for s in skills.columns:
        out[f"skill_{s}"] = skills[s].values
    out["translation_score"] = translation_score(skills).values
    age = meta["age_proxy"] if "age_proxy" in meta.columns else pd.Series(
        np.nan, index=meta.index)
    out["fit_score"] = fit_score(skills, age.reset_index(drop=True),
                                 need_weights, experience_weight).values
    out["translation_pct"] = out["translation_score"].rank(pct=True)
    out["fit_pct"] = out["fit_score"].rank(pct=True)
    return out

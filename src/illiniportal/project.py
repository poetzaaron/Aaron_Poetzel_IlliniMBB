"""Project any player's pre-transfer season onto a destination program.

Turns a set of pre-transfer player rows + a destination team into the
``{metric}_pre`` / ``delta_L`` / control layout the :class:`TranslationModel`
expects, then returns the projected post-transfer profile. This is what powers
both the Illinois target board and the backtest.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .model import TranslationModel

META_COLS = ["player", "pid", "team", "team_key", "conf", "year",
             "class", "age_proxy", "gp",
             # carried through for the pillar screen + expanded card (display only;
             # not features; the translation model is unchanged)
             "height", "height_in", "position", "pos_group",
             "three_pct", "tpa", "ft_pct", "rim_pct", "stl_pct", "blk_pct",
             "pts_pg", "ast_pg", "reb_pg", "oreb_pg", "dreb_pg"]


def projection_frame(players_pre: pd.DataFrame, teams: pd.DataFrame,
                     dest_team_key: str, dest_year: int, metrics: list[str]):
    """Build (X, meta) to project ``players_pre`` onto a destination program."""
    dest = teams[(teams["team_key"] == dest_team_key) & (teams["year"] == dest_year)]
    if dest.empty:
        raise ValueError(f"no team ratings for {dest_team_key!r} in {dest_year}")
    dest_adjem = float(dest["adjem"].iloc[0])

    pre = players_pre.merge(teams[["team_key", "year", "adjem"]],
                            on=["team_key", "year"], how="left")
    pre = pre.dropna(subset=["adjem"]).reset_index(drop=True)

    X = pd.DataFrame(index=pre.index)
    for m in metrics:
        X[f"{m}_pre"] = pd.to_numeric(pre[m], errors="coerce")
    X["delta_L"] = dest_adjem - pre["adjem"]
    X["usage_pre"] = pd.to_numeric(pre["usage"], errors="coerce")
    X["min_pct_pre"] = pd.to_numeric(pre["min_pct"], errors="coerce")
    X["gp_pre"] = pd.to_numeric(pre["gp"], errors="coerce")
    X["age_proxy_pre"] = pd.to_numeric(pre["age_proxy"], errors="coerce")

    meta = pre[[c for c in META_COLS if c in pre.columns]].copy()
    meta["dest_team_key"] = dest_team_key
    meta["dest_year"] = dest_year
    meta["delta_L"] = X["delta_L"].values
    return X, meta


def project(model: TranslationModel, X: pd.DataFrame) -> pd.DataFrame:
    """Run the model; return projected metrics with plain metric column names."""
    proj = model.predict(X)
    proj.columns = [c[:-5] if c.endswith("_proj") else c for c in proj.columns]
    return proj


def project_players(model, players_pre, teams, dest_team_key, dest_year):
    """Convenience: projection_frame -> project, returning (proj, meta)."""
    X, meta = projection_frame(players_pre, teams, dest_team_key, dest_year,
                               model.metrics)
    return project(model, X), meta

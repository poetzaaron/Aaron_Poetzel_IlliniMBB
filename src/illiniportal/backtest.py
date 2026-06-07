"""Retrospective validation of the engine on Illinois's own history.

Two-sided story:
  1. would the *fit* board have surfaced Underwood's actual signings?
  2. out-of-sample, do high *translation* grades actually keep producing while
     low grades fade? (the busts side)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fit, project
from .model import TranslationModel

ILLINOIS = "illinois"

# name substring, origin-team substring, pre-season year, destination year
SIGNINGS = [
    ("Terrence Shannon", "Texas Tech", 2022, 2023),
    ("Marcus Domask",    "Southern Illinois", 2023, 2024),
    ("Kylan Boswell",    "Arizona",    2024, 2025),
    ("Andrej Stojakovic","California",  2025, 2026),
]


def eligible_pool(players: pd.DataFrame, year: int,
                  min_pct: float = 40.0, gp: int = 15) -> pd.DataFrame:
    """Rotation players in a season: the realistic transfer-target universe."""
    p = players[players["year"] == year]
    return p[(p["min_pct"] >= min_pct) & (p["gp"] >= gp)].copy()


def transfer_pool(players: pd.DataFrame, pairs: pd.DataFrame, pre_year: int,
                  min_pct: float = 30.0) -> pd.DataFrame:
    """The *actual portal pool*: players who transferred after season ``pre_year``.

    Built from detected transfers, so it automatically excludes graduating
    seniors (who had no following season), i.e. only genuinely available
    players, the realistic universe a staff chooses from.
    """
    keys = set(pairs.loc[pairs["year_pre"] == pre_year, "player_key"])
    pids = {k.split("pid:")[-1] for k in keys if isinstance(k, str)}
    p = players[(players["year"] == pre_year)
                & (players["pid"].astype(str).isin(pids))]
    return p[p["min_pct"] >= min_pct].copy()


def _top_skills(board_row, n: int = 3) -> str:
    sk = {c[len("skill_"):]: float(board_row[c].iloc[0])
          for c in board_row.columns if c.startswith("skill_")}
    top = sorted(sk.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return ", ".join(f"{k} (+{v:.1f}z)" for k, v in top)


def _find(players, name, team, year):
    hit = players[(players["player"].str.contains(name, case=False, na=False))
                  & (players["team"].str.contains(team, case=False, na=False))
                  & (players["year"] == year)]
    return hit.iloc[0] if len(hit) else None


def flag_signings(model, players, teams, pairs) -> pd.DataFrame:
    """For each signing: where did the fit board rank them within the portal?"""
    rows = []
    for name, team, pre_year, dest_year in SIGNINGS:
        player = _find(players, name, team, pre_year)
        if player is None:
            rows.append({"player": name, "status": "not in data"})
            continue
        pool = transfer_pool(players, pairs, pre_year)
        proj, meta = project.project_players(model, pool, teams, ILLINOIS, dest_year)
        board = fit.score_pool(proj, meta).sort_values("fit_score", ascending=False)
        board = board.reset_index(drop=True)
        row = board[board["pid"].astype(str) == str(player["pid"])]
        if row.empty:
            rows.append({"player": name, "status": "below min-minutes filter"})
            continue
        rank = int(row.index[0]) + 1
        rows.append({
            "player": f"{name} ({team} {pre_year}->ILL {dest_year})",
            "portal_pool": len(board),
            "fit_rank": rank,
            "fit_pct": round(float(row["fit_pct"].iloc[0]) * 100, 1),
            "translation_pct": round(float(row["translation_pct"].iloc[0]) * 100, 1),
            "fits_because": _top_skills(row),
        })
    return pd.DataFrame(rows)


def projected_vs_actual(model, pairs, leave_one_out: bool = True) -> pd.DataFrame:
    """For each signing, the model's projection vs what actually happened.

    With ``leave_one_out`` (default), each signing is projected by a model
    re-fit *without that player's transfer*, so the projection is genuinely
    out-of-sample, not a memorised fit.
    """
    rows = []
    for name, team, pre_year, dest_year in SIGNINGS:
        m = pairs[(pairs["player_pre"].str.contains(name, case=False, na=False))
                  & (pairs["team_pre"].str.contains(team, case=False, na=False))
                  & (pairs["year_pre"] == pre_year)]
        if m.empty:
            continue
        i = m.index[0]
        if leave_one_out:
            pk = pairs.loc[i, "player_key"]
            mdl = TranslationModel().fit(pairs[pairs["player_key"] != pk])
        else:
            mdl = model
        proj = project.project(mdl, pairs.loc[[i]])
        for metric in ["usage", "ts", "ortg", "ast_pct", "min_pct"]:
            if f"{metric}_post" in pairs.columns:
                rows.append({
                    "player": name, "metric": metric,
                    "pre": round(float(pairs.loc[i, f"{metric}_pre"]), 1),
                    "projected": round(float(proj[metric].iloc[0]), 1),
                    "actual": round(float(pairs.loc[i, f"{metric}_post"]), 1),
                })
    return pd.DataFrame(rows)


def _production_composite(metric_frame: pd.DataFrame) -> pd.Series:
    """Translation-weighted composite of a frame whose cols are metric names."""
    skills = fit.skill_frame(metric_frame)
    return fit.translation_score(skills)


def separation(pairs, cutoff: int = 2023, n_groups: int = 4) -> pd.DataFrame:
    """Out-of-sample: do pre-signing translation grades predict actual outcome?

    Train on year_post<=cutoff; on the held-out test pairs, grade each transfer
    from its PRE season (projected to its actual destination) and bucket by
    grade. Report the mean ACTUAL post-transfer production composite per bucket.
    """
    train = pairs[pairs["year_post"] <= cutoff]
    test = pairs[pairs["year_post"] > cutoff].copy().reset_index(drop=True)
    model = TranslationModel().fit(train)

    proj = project.project(model, test)               # projected post (from pre)
    grade = _production_composite(proj)               # pre-signing grade

    actual_cols = {m: test[f"{m}_post"] for m in model.metrics
                   if f"{m}_post" in test.columns}
    actual = _production_composite(pd.DataFrame(actual_cols))

    df = pd.DataFrame({"grade": grade.values, "actual": actual.values}).dropna()
    df["bucket"] = pd.qcut(df["grade"], n_groups,
                           labels=[f"Q{i+1}" for i in range(n_groups)])
    tbl = (df.groupby("bucket", observed=True)
           .agg(n=("actual", "size"),
                mean_grade=("grade", "mean"),
                mean_actual_production=("actual", "mean"))
           .reset_index())
    tbl.attrs["spearman"] = df["grade"].corr(df["actual"], method="spearman")
    return tbl

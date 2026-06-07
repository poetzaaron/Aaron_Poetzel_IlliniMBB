"""Detect transfers from the player data itself.

A transfer is a player observed at team A in season ``t`` and a *different* D1
team B in season ``t+1`` (not a freshman with no prior year, not graduated with
no following year, not a same-team redshirt). Identity uses Torvik ``pid`` when
present, else a normalised name key with collision guards.
"""

from __future__ import annotations

import pandas as pd

from . import config


def _dedupe_player_seasons(players: pd.DataFrame):
    """One row per (player_key, year). Same-year multi-team rows are ambiguous.

    Returns (clean, ambiguous_keys). For ``name`` identity, a key appearing for
    >1 distinct team within a single season is almost certainly two different
    people, so those keys are dropped and reported.
    """
    counts = (players.groupby(["player_key", "year"])["team_key"]
              .nunique().reset_index(name="n_teams"))
    ambiguous = set(counts.loc[counts["n_teams"] > 1, "player_key"])

    clean = players[~players["player_key"].isin(ambiguous)].copy()
    # If a player legitimately has duplicate rows in a season, keep the one with
    # the most games (most complete record).
    sort_cols = ["player_key", "year"] + (["gp"] if "gp" in clean.columns else [])
    clean = (clean.sort_values(sort_cols)
             .drop_duplicates(["player_key", "year"], keep="last"))
    return clean, ambiguous


def detect_transfers(players: pd.DataFrame) -> pd.DataFrame:
    """Return one row per transfer instance with ``*_pre`` / ``*_post`` columns."""
    clean, ambiguous = _dedupe_player_seasons(players)

    metrics = [m for m in config.METRICS if m in clean.columns]
    carry = ["player", "team", "team_key", "conf", "year", "gp",
             "age_proxy", "id_kind"] + metrics
    carry = [c for c in dict.fromkeys(carry) if c in clean.columns]

    clean = clean.sort_values(["player_key", "year"])
    nxt = clean.groupby("player_key").shift(-1)

    pairs = pd.DataFrame({"player_key": clean["player_key"].values})
    for c in carry:
        pairs[f"{c}_pre"] = clean[c].values
        pairs[f"{c}_post"] = nxt[c].values

    pairs = pairs.dropna(subset=["year_post"])
    pairs["year_pre"] = pairs["year_pre"].astype(int)
    pairs["year_post"] = pairs["year_post"].astype(int)

    is_transfer = (
        (pairs["year_post"] == pairs["year_pre"] + 1)      # consecutive seasons
        & (pairs["team_key_pre"] != pairs["team_key_post"])  # changed schools
    )
    pairs = pairs[is_transfer].reset_index(drop=True)
    pairs.attrs["ambiguous_name_keys"] = len(ambiguous)
    return pairs


def attach_team_strength(pairs: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Join origin/destination team ratings and compute the level jump ΔL."""
    t = teams[["team_key", "year", "adjoe", "adjde", "adjem", "barthag", "sos"]]
    # add_suffix turns team_key/year into the join keys already present on pairs.
    out = pairs.merge(
        t.add_suffix("_pre"), on=["team_key_pre", "year_pre"], how="left",
    ).merge(
        t.add_suffix("_post"), on=["team_key_post", "year_post"], how="left",
    )
    # Level jump: positive => moving UP to a stronger program.
    out["delta_L"] = out["adjem_post"] - out["adjem_pre"]
    out["delta_sos"] = out["sos_post"] - out["sos_pre"]
    out["delta_barthag"] = out["barthag_post"] - out["barthag_pre"]
    return out

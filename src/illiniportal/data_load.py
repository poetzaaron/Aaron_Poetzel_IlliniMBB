"""Load and normalise Torvik player & team exports into tidy frames.

Both files come from Torvik so team names already agree; we still apply a light
``team_key`` so joins are robust to whitespace/case. The loader is alias-driven
(:func:`config.canonical_name`) and tolerant of extra columns.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_YEAR_RE = re.compile(r"(20\d{2})")


def name_key(name) -> str:
    """Normalised player name used for identity when no ``pid`` is present."""
    s = str(name).lower().strip()
    s = re.sub(r"[.'`’]", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def team_key(name) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


_HT_RE = re.compile(r"(\d+)\s*-\s*(\d+)")


def height_inches(value) -> float:
    """Parse a Torvik height string ("6-4") to inches; NaN if unparseable."""
    m = _HT_RE.search(str(value))
    return float(int(m.group(1)) * 12 + int(m.group(2))) if m else np.nan


def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    rename, taken = {}, set()
    for col in df.columns:
        canon = config.canonical_name(col)
        if canon and canon not in taken:
            rename[col] = canon
            taken.add(canon)
    return df.rename(columns=rename)


def _infer_year(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    if "year" in df.columns and df["year"].notna().any():
        return df
    m = _YEAR_RE.search(path.stem)
    if not m:
        raise ValueError(
            f"{path.name}: no 'year'/'season' column and no year in filename"
        )
    df = df.copy()
    df["year"] = int(m.group(1))
    return df


def _collect_paths(raw_dir: Path, globs) -> list[Path]:
    seen, paths = set(), []
    for pat in globs:
        for p in sorted(raw_dir.glob(pat)):
            if p.name.startswith(".") or p in seen:
                continue
            seen.add(p)
            paths.append(p)
    return paths


def _looks_like_header(row) -> bool:
    """A row is a header if several of its cells map to canonical names."""
    hits = sum(config.canonical_name(c) is not None for c in row)
    return hits >= 3


def _read_player_file(path: Path) -> pd.DataFrame:
    """Read one player export, handling Torvik's headerless positional format."""
    raw = pd.read_csv(path, header=None, dtype=str)
    if _looks_like_header(raw.iloc[0].tolist()):
        df = pd.read_csv(path)            # has a real header
        df = _apply_aliases(df)
    else:                                  # positional Torvik export
        keep = {i: name for i, name in config.POSITIONAL_PLAYER.items()
                if i < raw.shape[1]}
        df = raw[list(keep)].rename(columns=keep)
    return _infer_year(df, path)


def _read_team_file(path: Path) -> pd.DataFrame:
    return _infer_year(_apply_aliases(pd.read_csv(path)), path)


def _to_num(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _class_to_years(value) -> float:
    if pd.isna(value):
        return np.nan
    return config.CLASS_TO_YEARS.get(config._norm(value), np.nan)


def load_players(raw_dir: Path | None = None) -> pd.DataFrame:
    raw_dir = Path(raw_dir) if raw_dir else config.DATA_RAW
    paths = _collect_paths(raw_dir, config.PLAYER_GLOBS)
    if not paths:
        raise FileNotFoundError(
            f"No player files in {raw_dir} (looked for {config.PLAYER_GLOBS})."
        )
    df = pd.concat([_read_player_file(p) for p in paths], ignore_index=True)
    pillar_num = ["ft_pct", "two_pct", "tpm", "tpa", "three_pct", "blk_pct",
                  "stl_pct", "rim_pct", "mid_pct", "oreb_pg", "dreb_pg",
                  "reb_pg", "ast_pg", "stl_pg", "blk_pg", "pts_pg"]
    df = _to_num(df, ["year", "gp", "pts"] + config.METRICS + pillar_num)
    # FT/2P/3P/rim/mid% arrive as 0-1 fractions in the positional export; lift to
    # the 0-100 scale the other rate stats use (guarded so header 0-100 data is
    # left alone).
    for c in config.PCT01_COLS:
        if c in df.columns and df[c].notna().any() and df[c].max() <= 1.5:
            df[c] = df[c] * 100.0
    df["year"] = df["year"].astype("Int64")
    df = df[df["year"].between(config.YEAR_MIN, config.YEAR_MAX)].copy()

    df["name_key"] = df["player"].map(name_key)
    df["team_key"] = df["team"].map(team_key)
    has_pid = "pid" in df.columns and df["pid"].notna()
    if "pid" not in df.columns:
        df["pid"] = pd.NA
        has_pid = pd.Series(False, index=df.index)
    df["id_kind"] = np.where(has_pid, "pid", "name")
    df["player_key"] = np.where(
        has_pid, "pid:" + df["pid"].astype(str), "nm:" + df["name_key"]
    )

    if "class" in df.columns:
        df["age_proxy"] = df["class"].map(_class_to_years)
    else:
        df["age_proxy"] = np.nan

    # positional size needs height-in-inches and a coarse position group.
    df["height_in"] = df["height"].map(height_inches) if "height" in df.columns \
        else np.nan
    pos = df["position"] if "position" in df.columns else pd.Series("", index=df.index)
    df["pos_group"] = [config.position_group(p, h)
                       for p, h in zip(pos, df["height_in"])]
    return df


def load_teams(raw_dir: Path | None = None) -> pd.DataFrame:
    raw_dir = Path(raw_dir) if raw_dir else config.DATA_RAW
    paths = _collect_paths(raw_dir, config.TEAM_GLOBS)
    if not paths:
        raise FileNotFoundError(
            f"No team files in {raw_dir} (looked for {config.TEAM_GLOBS})."
        )
    df = pd.concat([_read_team_file(p) for p in paths], ignore_index=True)
    df = _to_num(df, ["year", "adjoe", "adjde", "barthag", "sos"])
    df["year"] = df["year"].astype("Int64")
    df = df[df["year"].between(config.YEAR_MIN, config.YEAR_MAX)].copy()
    df["team_key"] = df["team"].map(team_key)

    # adjEM is the primary level measure; barthag/sos are alternates.
    if {"adjoe", "adjde"}.issubset(df.columns):
        df["adjem"] = df["adjoe"] - df["adjde"]
    else:
        df["adjem"] = np.nan
    return df[["team_key", "team", "conf", "year", "adjoe", "adjde",
               "adjem", "barthag", "sos"]].drop_duplicates(["team_key", "year"])


def available_metrics(players: pd.DataFrame) -> list[str]:
    """Metrics actually present (non-empty) in the player data."""
    return [m for m in config.METRICS
            if m in players.columns and players[m].notna().any()]

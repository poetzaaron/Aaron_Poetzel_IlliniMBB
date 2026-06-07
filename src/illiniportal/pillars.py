"""Stage 1: the four-pillar screen (size · skill · IQ · character).

A screening layer that runs *in front of* the translation/fit engine. It
operationalizes the framework Illinois's GM described publicly: gate players on
positional **size**, **skill** deficiencies, basketball-**IQ** (a proxy), and
**character** (manual), then let the existing engine rank the survivors.

Design rules (load-bearing):
- Floors and flags, **not** a weighted average. One strength cannot offset a
  disqualifying weakness; shooting is the canonical disqualifier and is weighted
  hardest inside the skill pillar.
- Pillars set **eligibility**, never a score. Nothing here writes to ``fit_score``
  or ``translation_score``; the board demotes flagged players, but their score is
  untouched (the model stays free to disagree with the staff).
- A **fifth** pillar, *fouling discipline*, is part of the framework but
  **data-blocked**: the Torvik export carries no fouls-committed / opponent
  free-throw-rate field. It is reported as ``blocked``, not silently dropped.

Stats are read from a player's pre-transfer season (who they actually are).
Percentile floors are taken **within position group** against the full D1 season
population, so a guard is measured against guards, not against centers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# pillars whose status can auto-demote a player (character is manual, fouling
# is data-blocked; neither auto-flags).
ACTIVE_GATES = ["size", "skill", "iq", "character"]


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _pctile_within_group(values: pd.Series, groups: pd.Series,
                         ref_values: pd.Series, ref_groups: pd.Series) -> pd.Series:
    """Percentile (0-100) of each value vs reference values of the same group."""
    ref = pd.DataFrame({"g": ref_groups.values,
                        "v": pd.to_numeric(ref_values, errors="coerce").values}).dropna()
    sorted_by_group = {g: np.sort(sub["v"].values) for g, sub in ref.groupby("g")}
    out = np.full(len(values), np.nan)
    v = values.to_numpy(dtype="float64")
    g = groups.to_numpy()
    for i in range(len(v)):
        arr = sorted_by_group.get(g[i])
        if arr is None or len(arr) == 0 or np.isnan(v[i]):
            continue
        out[i] = np.searchsorted(arr, v[i], side="right") / len(arr) * 100.0
    return pd.Series(out, index=values.index)


def _status_from_pctile(pct: pd.Series, flag: float, warn: float) -> pd.Series:
    s = pd.Series("na", index=pct.index, dtype=object)
    ok = pct.notna()
    s[ok] = "pass"
    s[ok & (pct < warn)] = "warn"
    s[ok & (pct < flag)] = "flag"
    return s


def pillar_status(pool: pd.DataFrame, reference: pd.DataFrame,
                  thresholds: dict | None = None) -> pd.DataFrame:
    """Per-player pillar verdicts for ``pool`` (keyed by ``pid``).

    ``reference`` is the full season player population used for within-position
    percentiles. Returns one row per pool player with a ``pass``/``warn``/``flag``
    status (plus ``na``/``manual``/``blocked``) and a one-line reason per pillar.
    """
    th = {**config.PILLAR_DEFAULTS, **(thresholds or {})}
    idx = pool.index
    grp = pool["pos_group"] if "pos_group" in pool.columns else pd.Series(None, index=idx)
    grp_lbl = grp.map(config.GROUP_LABELS).fillna("n/a")
    ref_grp = reference["pos_group"] if "pos_group" in reference.columns \
        else pd.Series(None, index=reference.index)

    out = pd.DataFrame(index=idx)
    out["pid"] = pool["pid"].astype(str).values if "pid" in pool.columns else idx

    # --- 1. positional size ------------------------------------------------
    ht = _num(pool, "height_in")
    size_pct = _pctile_within_group(ht, grp, _num(reference, "height_in"), ref_grp)
    out["size_pctile"] = size_pct
    out["size_status"] = _status_from_pctile(
        size_pct, th["size_pctile_flag"], th["size_pctile_warn"])
    htxt = pool["height"] if "height" in pool.columns else pd.Series("", index=idx)
    out["size_reason"] = [
        (f"{h} · {p:.0f}th %ile ht for {g}" if pd.notna(p)
         else "height unavailable")
        for h, p, g in zip(htxt, size_pct, grp_lbl)]

    # --- 2. skill (shooting weighted hardest) ------------------------------
    ts, three = _num(pool, "ts"), _num(pool, "three_pct")
    tpa, ft = _num(pool, "tpa"), _num(pool, "ft_pct")
    ts_red = (ts < th["shoot_ts_floor"]).fillna(False)
    three_red = ((tpa >= th["shoot_three_min_att"]) &
                 (three < th["shoot_three_floor"])).fillna(False)
    ft_red = (ft < th["shoot_ft_floor"]).fillna(False)
    reds = ts_red.astype(int) + three_red.astype(int) + ft_red.astype(int)
    have_shot = ts.notna() | three.notna() | ft.notna()
    shooting = pd.Series("na", index=idx, dtype=object)
    shooting[have_shot] = "pass"
    shooting[have_shot & (reds == 1)] = "warn"
    shooting[have_shot & (reds >= 2)] = "flag"

    rim = _status_from_pctile(
        _pctile_within_group(_num(pool, "rim_pct"), grp,
                             _num(reference, "rim_pct"), ref_grp),
        th["skill_pctile_flag"], th["skill_pctile_warn"])
    reb = _status_from_pctile(
        _pctile_within_group(_num(pool, "orb_pct") + _num(pool, "drb_pct"), grp,
                             _num(reference, "orb_pct") + _num(reference, "drb_pct"),
                             ref_grp),
        th["skill_pctile_flag"], th["skill_pctile_warn"])
    passing = _status_from_pctile(
        _pctile_within_group(_num(pool, "ast_pct"), grp,
                             _num(reference, "ast_pct"), ref_grp),
        th["skill_pctile_flag"], th["skill_pctile_warn"])
    defense = _status_from_pctile(
        _pctile_within_group(_num(pool, "stl_pct") + _num(pool, "blk_pct"), grp,
                             _num(reference, "stl_pct") + _num(reference, "blk_pct"),
                             ref_grp),
        th["skill_pctile_flag"], th["skill_pctile_warn"])
    out["shooting_status"] = shooting
    out["rim_status"], out["rebounding_status"] = rim, reb
    out["passing_status"], out["defense_status"] = passing, defense

    others = pd.DataFrame({"rim": rim, "reb": reb, "pas": passing, "dfn": defense})
    n_other_flags = (others == "flag").sum(axis=1)
    skill = pd.Series("pass", index=idx, dtype=object)
    skill[(shooting == "warn") | (n_other_flags == 1)] = "warn"
    skill[n_other_flags >= 2] = "flag"
    skill[shooting == "flag"] = "flag"          # shooting is the canonical disqualifier
    out["skill_status"] = skill

    _LBL = {"shooting": "shooting", "rim": "rim finishing", "reb": "rebounding",
            "pas": "passing", "dfn": "defensive activity"}

    def _skill_reason(row_i):
        bad = []
        if shooting.iloc[row_i] in ("flag", "warn"):
            bad.append(_LBL["shooting"])
        for k, s in [("rim", rim), ("reb", reb), ("pas", passing), ("dfn", defense)]:
            if s.iloc[row_i] == "flag":
                bad.append(_LBL[k])
        if not bad:
            return "no skill below floor"
        return "below floor: " + ", ".join(bad)

    out["skill_reason"] = [_skill_reason(i) for i in range(len(idx))]

    # --- 3. basketball-IQ proxy (AST:TO, ranked within position) -----------
    ratio = _num(pool, "ast_pct") / _num(pool, "to_pct").replace(0, np.nan)
    ref_ratio = (_num(reference, "ast_pct")
                 / _num(reference, "to_pct").replace(0, np.nan))
    iq_pct = _pctile_within_group(ratio, grp, ref_ratio, ref_grp)
    iq = _status_from_pctile(iq_pct, th["iq_pctile_flag"], th["iq_pctile_warn"])
    out["iq_ratio"] = ratio
    out["iq_status"] = iq
    out["iq_reason"] = [
        (f"AST:TO ≈ {r:.2f} · {q:.0f}th %ile for {g} (proxy)"
         if pd.notna(r) and pd.notna(q) else "AST:TO unavailable")
        for r, q, g in zip(ratio, iq_pct, grp_lbl)]

    # --- 4. character (manual) & 5. fouling (data-blocked) -----------------
    out["character_status"] = "manual"
    out["fouling_status"] = "blocked"

    # demote flag: any AUTO active gate flagged (character is manual; fouling blocked)
    out["pillar_flag"] = ((out["size_status"] == "flag")
                          | (out["skill_status"] == "flag")
                          | (out["iq_status"] == "flag"))

    def _summary(i):
        bits = []
        if out["size_status"].iloc[i] == "flag":
            bits.append("size")
        if out["skill_status"].iloc[i] == "flag":
            bits.append("skill")
        if out["iq_status"].iloc[i] == "flag":
            bits.append("IQ")
        return "flags: " + ", ".join(bits) if bits else "clears active gates"

    out["pillar_summary"] = [_summary(i) for i in range(len(idx))]
    return out.reset_index(drop=True)

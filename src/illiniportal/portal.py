"""Forward-mode portal ingestion.

The upcoming 2026-27 portal can't be detected from completed-season data, so the
entrant list is an external input (``data/raw/portal_2026.csv``). We already hold
every entrant's pre-portal (2025-26 == ``year==2026``) stats, so matching the list
to those rows yields a projectable pool. A player with no 2025-26 D1 season
(international/JUCO) can't be projected, and is reported as unmatched.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import data_load

PORTAL_SEASON = 2026  # 2025-26 stats = the pre-portal season for 2026-27 movement

# light first-name variant recovery (Mike -> Michael, etc.)
_FIRST_VARIANTS = {
    "mike": "michael", "matt": "matthew", "chris": "christopher",
    "nick": "nicholas", "joe": "joseph", "ben": "benjamin", "alex": "alexander",
    "tim": "timothy", "dave": "david", "danny": "daniel", "jake": "jacob",
    "sam": "samuel", "tony": "anthony", "will": "william", "rob": "robert",
    "gabe": "gabriel", "nate": "nathan", "ed": "edward", "jp": "jp",
}

_PLAYER_H = {"player", "name", "fullname"}
_TEAM_H = {"fromteam", "from", "school", "prevteam", "previousschool", "team", "origin"}
_PID_H = {"pid", "playerid", "id"}
_DEST_H = {"committedto", "committed", "destination", "signed", "to", "newschool"}


def _norm_h(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def find_portal_file(raw_dir) -> Path | None:
    raw_dir = Path(raw_dir)
    hits = [h for h in sorted(raw_dir.glob("portal_*.csv"))
            if "template" not in h.name and not h.name.startswith(".")]
    return hits[-1] if hits else None


def load_portal(path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    rename = {}
    for c in df.columns:
        n = _norm_h(c)
        if n in _PLAYER_H:
            rename[c] = "player"
        elif n in _TEAM_H:
            rename[c] = "from_team"
        elif n in _PID_H:
            rename[c] = "pid"
        elif n in _DEST_H:
            rename[c] = "committed_to"
    df = df.rename(columns=rename)
    if "player" not in df.columns:               # assume first column is the name
        df = df.rename(columns={df.columns[0]: "player"})
    df = df[df["player"].notna() & (df["player"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def _variant_key(nk: str):
    parts = nk.split()
    if parts and parts[0] in _FIRST_VARIANTS:
        parts[0] = _FIRST_VARIANTS[parts[0]]
        return " ".join(parts)
    return None


def forward_pool(players: pd.DataFrame, portal: pd.DataFrame,
                 season: int = PORTAL_SEASON):
    """Match entrants to their ``season`` rows. Returns ``(pool, report)``.

    ``pool`` is the matched subset of ``players`` plus ``committed_to`` /
    ``match_kind``; homonyms resolve to the highest-minutes player and are flagged.
    """
    pf = players[players["year"] == season].copy()
    pf["name_key"] = pf["player"].map(data_load.name_key)
    pf["team_key"] = pf["team"].map(data_load.team_key)
    if "min_pct" in pf.columns:                  # so homonyms resolve to the regular
        pf = pf.sort_values("min_pct", ascending=False)

    has_pid = "pid" in pf.columns
    by_pid = {str(r["pid"]): i for i, r in pf.iterrows()} if has_pid else {}
    by_name: dict[str, list] = {}
    for i, r in pf.iterrows():
        by_name.setdefault(r["name_key"], []).append(i)

    rows, kinds, dests, ambiguous, unmatched = [], [], [], [], []
    has = portal.columns
    for _, p in portal.iterrows():
        pid = str(p["pid"]).strip() if "pid" in has and pd.notna(p.get("pid")) else ""
        nk = data_load.name_key(p["player"])
        tk = (data_load.team_key(p["from_team"])
              if "from_team" in has and pd.notna(p.get("from_team")) else None)

        idx = kind = None
        if pid and pid in by_pid:
            idx, kind = by_pid[pid], "pid"
        else:
            cands = by_name.get(nk, [])
            if tk:
                cands = [i for i in cands if pf.at[i, "team_key"] == tk] or cands
            if len(cands) == 1:
                idx, kind = cands[0], "name"
            elif len(cands) > 1:
                idx, kind = cands[0], "ambiguous"   # pf sorted by min_pct desc
                ambiguous.append(p["player"])
            else:
                vk = _variant_key(nk)
                vcands = by_name.get(vk, []) if vk else []
                if vcands:
                    idx, kind = vcands[0], "variant"
                else:
                    unmatched.append(p["player"])
        if idx is not None:
            rows.append(idx)
            kinds.append(kind)
            dests.append(str(p["committed_to"]).strip()
                         if "committed_to" in has and pd.notna(p.get("committed_to"))
                         else "")

    pool = pf.loc[rows].copy()
    pool["match_kind"] = kinds
    pool["committed_to"] = dests
    if has_pid:
        pool = pool.drop_duplicates("pid")
    report = {"total": len(portal), "matched": len(pool),
              "ambiguous": ambiguous, "unmatched": unmatched}
    return pool.reset_index(drop=True), report

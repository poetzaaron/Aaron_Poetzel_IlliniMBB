"""Generate Torvik-shaped SYNTHETIC data to smoke-test the pipeline offline.

Writes player_<year>.csv / team_<year>.csv into ``data/sample/`` using Torvik-ish
header spellings (usg, Min_per, TS_per, adj_o, ...) so the alias mapping is
exercised. Stats are generated so they depend on team strength, which gives the
translation model real ΔL signal. A few known Illinois transfers are injected so
the sanity report has something to find.

    python scripts/make_synthetic_data.py [--out data/sample]
"""

import argparse
from pathlib import Path

import _pathsetup  # noqa: F401

import numpy as np
import pandas as pd

YEARS = list(range(2022, 2027))  # mirror the real data range (2022-2026)
SEED = 7

REAL_TEAMS = {  # name -> latent strength (adjEM-ish)
    "Illinois": 18.0, "Texas Tech": 14.0, "Arizona": 16.0, "California": -2.0,
    "Stanford": 4.0, "Purdue": 20.0, "Indiana": 8.0,
}
N_GENERIC = 110

# (name, pid, pre_year, pre_team, post_team): injected known transfers.
KNOWN_TRANSFERS = [
    ("Terrence Shannon", 900001, 2022, "Texas Tech", "Illinois"),
    ("Kylan Boswell", 900002, 2024, "Arizona", "Illinois"),
    ("Andrej Stojakovic", 900003, 2024, "California", "Illinois"),
]


def build_teams(rng):
    names = list(REAL_TEAMS) + [f"Team{ i:03d}" for i in range(N_GENERIC)]
    base = dict(REAL_TEAMS)
    for n in names:
        if n not in base:
            base[n] = float(rng.normal(0, 9))
    rows = []
    for yr in YEARS:
        for n in names:
            adjem = base[n] + rng.normal(0, 1.5)  # small year drift
            adjo = 104 + adjem / 2 + rng.normal(0, 1)
            adjd = 104 - adjem / 2 + rng.normal(0, 1)
            barthag = 1 / (1 + np.exp(-adjem / 10))
            sos = adjem * 0.4 + rng.normal(0, 3)
            rows.append(dict(team=n, conf="Cxx", year=yr,
                             adj_o=round(adjo, 1), adj_d=round(adjd, 1),
                             barthag=round(barthag, 4), sos=round(sos, 2)))
    teams = pd.DataFrame(rows)
    strength = {(r.team, r.year): r.adj_o - r.adj_d
                for r in teams.itertuples()}
    return teams, strength, names


def _stat_row(rng, z, adjem, is_big):
    usage = np.clip(20 + 4.5 * z - 0.30 * adjem + rng.normal(0, 3), 6, 36)
    efg = np.clip(50 + 5 * z - 0.15 * adjem + rng.normal(0, 4), 35, 70)
    return dict(
        min_per=round(float(np.clip(45 + 10 * z - 0.1 * adjem + rng.normal(0, 8), 5, 98)), 1),
        usg=round(float(usage), 1),
        ortg=round(float(np.clip(102 + 6 * z - 0.20 * (usage - 20) - 0.25 * adjem + rng.normal(0, 6), 75, 135)), 1),
        efg=round(float(efg), 1),
        ts_per=round(float(np.clip(efg + 4 + rng.normal(0, 2), 38, 75)), 1),
        orb_per=round(float(np.clip(5 + 4 * is_big + 1.5 * z + rng.normal(0, 1.5), 0.5, 18)), 1),
        drb_per=round(float(np.clip(12 + 6 * is_big + 1.5 * z + rng.normal(0, 2), 3, 30)), 1),
        ast_per=round(float(np.clip(15 - 6 * is_big + 2.5 * z - 0.05 * adjem + rng.normal(0, 4), 1, 45)), 1),
        to_per=round(float(np.clip(16 - 1.5 * z + 0.10 * adjem + rng.normal(0, 3), 5, 35)), 1),
    )


CLASSES = ["Fr", "So", "Jr", "Sr"]


def build_players(rng, strength, names):
    records = []
    pid = 1

    def emit(name, pid, team, year, z, is_big, cls):
        adjem = strength[(team, year)]
        row = dict(player_name=name, pid=pid, team=team, conf="Cxx", year=year,
                   g=int(rng.integers(20, 35)), yr=cls,
                   pos="C" if is_big else "G", ht="6-5",
                   obpm=round(float(2 * z + rng.normal(0, 1)), 1),
                   dbpm=round(float(z + rng.normal(0, 1)), 1),
                   bpm=round(float(3 * z + rng.normal(0, 1)), 1),
                   pts=round(float(np.clip(8 + 5 * z + rng.normal(0, 3), 0, 30)), 1))
        row.update(_stat_row(rng, z, adjem, is_big))
        records.append(row)

    # generic careers
    for _ in range(1400):
        z = float(rng.normal(0, 1))
        is_big = int(rng.random() < 0.4)
        start = int(rng.choice(YEARS[:-1]))
        length = int(rng.integers(2, 5))
        career_years = [y for y in range(start, start + length) if y in YEARS]
        if len(career_years) < 2:
            continue
        team = str(rng.choice(names))
        transfer_at = (rng.integers(1, len(career_years))
                       if rng.random() < 0.35 else None)
        for i, yr in enumerate(career_years):
            if transfer_at is not None and i == transfer_at:
                team = str(rng.choice(names))  # change schools
            cls = CLASSES[min(i, 3)]
            emit(f"Gen Player{pid}", pid, team, yr, z, is_big, cls)
        pid += 1

    # injected known transfers (high skill)
    for name, kpid, pre_year, pre_team, post_team in KNOWN_TRANSFERS:
        z = 2.2
        emit(name, kpid, pre_team, pre_year, z, 0, "Jr")
        emit(name, kpid, post_team, pre_year + 1, z, 0, "Sr")

    return pd.DataFrame(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sample")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    teams, strength, names = build_teams(rng)
    players = build_players(rng, strength, names)

    for yr in YEARS:
        players[players["year"] == yr].to_csv(out / f"player_{yr}.csv", index=False)
        teams[teams["year"] == yr].to_csv(out / f"team_{yr}.csv", index=False)
    print(f"wrote synthetic data for {YEARS[0]}-{YEARS[-1]} -> {out} "
          f"({len(players):,} player-seasons, {len(teams):,} team-seasons)")


if __name__ == "__main__":
    main()

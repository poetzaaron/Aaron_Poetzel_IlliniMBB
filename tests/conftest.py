"""Shared fixtures: hand-built frames for unit logic + a synthetic end-to-end set."""

import numpy as np
import pandas as pd
import pytest

from illiniportal import config


def player_row(player_key, player, team_key, year, *, id_kind="pid",
               gp=25, age=2, base=30.0):
    """A single player-season row in the shape detect_transfers expects."""
    rng = np.random.default_rng(abs(hash((player_key, year))) % (2**32))
    row = dict(player_key=player_key, id_kind=id_kind, player=player,
               team_key=team_key, team=team_key.title(), conf="C",
               year=year, gp=gp, age_proxy=age, name_key=player.lower(),
               pid=player_key.split(":")[-1])
    for m in config.METRICS:
        row[m] = float(base + rng.uniform(-5, 5))
    return row


@pytest.fixture
def players_small():
    """Covers transfer, same-team stay, year gap, graduation, and ambiguity."""
    rows = [
        # P1 transfers X(2022) -> Y(2023): a valid transfer
        player_row("pid:1", "Al Pha", "x", 2022),
        player_row("pid:1", "Al Pha", "y", 2023),
        # P2 stays at X both years: not a transfer
        player_row("pid:2", "Be Ta", "x", 2022),
        player_row("pid:2", "Be Ta", "x", 2023),
        # P3 has a gap (2022 then 2024): not consecutive
        player_row("pid:3", "Ga Mma", "x", 2022),
        player_row("pid:3", "Ga Mma", "y", 2024),
        # P4 single season then gone: graduated
        player_row("pid:4", "De Lta", "x", 2022),
        # Name-identity homonyms in same season at different teams: ambiguous
        player_row("nm:ho mon", "Ho Mon", "x", 2022, id_kind="name"),
        player_row("nm:ho mon", "Ho Mon", "z", 2022, id_kind="name"),
        player_row("nm:ho mon", "Ho Mon", "y", 2023, id_kind="name"),
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def teams_small():
    rows = []
    strengths = {"x": -5.0, "y": 15.0, "z": 0.0}
    for yr in (2022, 2023, 2024):
        for tk, s in strengths.items():
            rows.append(dict(team_key=tk, team=tk.title(), conf="C", year=yr,
                             adjoe=104 + s / 2, adjde=104 - s / 2, adjem=s,
                             barthag=0.5, sos=s * 0.4))
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def synth_dir(tmp_path_factory):
    """Generate Torvik-shaped synthetic CSVs once; return the directory."""
    import make_synthetic_data as msd

    out = tmp_path_factory.mktemp("synth")
    rng = np.random.default_rng(msd.SEED)
    teams, strength, names = msd.build_teams(rng)
    players = msd.build_players(rng, strength, names)
    for yr in msd.YEARS:
        players[players["year"] == yr].to_csv(out / f"player_{yr}.csv", index=False)
        teams[teams["year"] == yr].to_csv(out / f"team_{yr}.csv", index=False)
    return out


@pytest.fixture(scope="session")
def synth_pairs(synth_dir):
    from illiniportal import data_load, transfers
    players = data_load.load_players(synth_dir)
    teams = data_load.load_teams(synth_dir)
    pairs = transfers.detect_transfers(players)
    return transfers.attach_team_strength(pairs, teams)

from illiniportal import transfers


def test_detect_only_real_transfers(players_small):
    pairs = transfers.detect_transfers(players_small)
    # Only pid:1 (x 2022 -> y 2023) qualifies.
    assert len(pairs) == 1
    row = pairs.iloc[0]
    assert row["player_key"] == "pid:1"
    assert row["team_key_pre"] == "x" and row["team_key_post"] == "y"
    assert int(row["year_pre"]) == 2022 and int(row["year_post"]) == 2023


def test_ambiguous_name_excluded(players_small):
    pairs = transfers.detect_transfers(players_small)
    assert pairs.attrs["ambiguous_name_keys"] == 1
    assert "nm:ho mon" not in set(pairs["player_key"])


def test_same_team_and_gap_excluded(players_small):
    pairs = transfers.detect_transfers(players_small)
    keys = set(pairs["player_key"])
    assert "pid:2" not in keys  # stayed at same school
    assert "pid:3" not in keys  # non-consecutive seasons
    assert "pid:4" not in keys  # graduated (no following season)


def test_attach_team_strength_delta(players_small, teams_small):
    pairs = transfers.detect_transfers(players_small)
    out = transfers.attach_team_strength(pairs, teams_small)
    # x adjem=-5, y adjem=+15  =>  ΔL = 20 (moving up)
    assert abs(out["delta_L"].iloc[0] - 20.0) < 1e-6

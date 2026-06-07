import pandas as pd

from illiniportal import config, data_load


def test_name_key_strips_suffix_and_punct():
    assert data_load.name_key("D'Angelo Russell Jr.") == "dangelo russell"
    assert data_load.name_key("Terrence Shannon III") == "terrence shannon"
    assert data_load.name_key("Zach  Edey") == "zach edey"


def test_team_key_normalises():
    assert data_load.team_key("  Texas Tech ") == "texas tech"
    assert data_load.team_key("Grambling St.") == "grambling st."


def test_header_detection():
    assert data_load._looks_like_header(["player", "team", "conf", "usg"])
    assert not data_load._looks_like_header(["DeJuan Clayton", "Manhattan", "MAAC"])


def test_positional_player_file(tmp_path):
    ncols = 40
    r = ["0"] * ncols
    r[0], r[1], r[2], r[3], r[4], r[5], r[6] = \
        "Test Player", "Test Team", "CONF", "25", "50.0", "110", "20"
    r[7], r[8], r[9], r[10], r[11], r[12] = "52", "55", "5", "15", "18", "12"
    r[25], r[26], r[31], r[32] = "Sr", "6-5", "2024", "99999"
    path = tmp_path / "player_2024.csv"
    pd.DataFrame([r, r]).to_csv(path, index=False, header=False)

    df = data_load._read_player_file(path)
    assert {"player", "team", "year", "pid", "usage", "ts"} <= set(df.columns)
    assert df["player"].iloc[0] == "Test Player"
    assert str(df["pid"].iloc[0]) == "99999"
    assert int(df["year"].iloc[0]) == 2024


def test_positional_loads_and_rescales_pillar_stats(tmp_path):
    ncols = 67
    r = ["0"] * ncols
    (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]) = \
        "Guard Test", "Team", "CONF", "30", "60", "112", "22", "53", "58"
    r[9], r[10], r[11], r[12] = "3", "12", "25", "12"
    r[15] = "0.82"                       # FT% stored as 0-1
    r[19], r[20], r[21] = "60", "160", "0.40"   # 3PM, 3PA, 3P% (0-1)
    r[22], r[23] = "1.0", "3.0"          # blk%, stl% already on 0-100
    r[25], r[26] = "Jr", "6-3"
    r[31], r[32] = "2024", "77777"
    r[40] = "0.60"                       # rim% (0-1)
    r[57], r[58], r[59], r[60], r[61], r[62], r[63] = \
        "1.0", "3.0", "4.0", "5.0", "1.5", "0.3", "15.0"
    r[64] = "Combo G"
    pd.DataFrame([r, r]).to_csv(tmp_path / "player_2024.csv", index=False, header=False)

    row = data_load.load_players(tmp_path).iloc[0]
    assert abs(row["three_pct"] - 40.0) < 1e-6   # 0-1 lifted to 0-100
    assert abs(row["ft_pct"] - 82.0) < 1e-6
    assert abs(row["rim_pct"] - 60.0) < 1e-6
    assert abs(row["stl_pct"] - 3.0) < 1e-6      # native 0-100 left alone
    assert abs(row["pts_pg"] - 15.0) < 1e-6
    assert row["pos_group"] == "G" and row["height_in"] == 75.0


def test_load_players_builds_identity(synth_dir):
    players = data_load.load_players(synth_dir)
    assert (players["id_kind"] == "pid").all()
    assert players["player_key"].str.startswith("pid:").all()
    assert players["year"].between(config.YEAR_MIN, config.YEAR_MAX).all()
    assert players["age_proxy"].notna().mean() > 0.9


def test_load_players_name_identity_fallback(tmp_path):
    # A headered export with no pid column -> identity falls back to name key.
    df = pd.DataFrame({
        "player": ["Joe Guard", "Max Wing"], "team": ["Duke", "Duke"],
        "conf": ["ACC", "ACC"], "year": [2024, 2024],
        "usg": [22, 18], "ortg": [110, 105], "efg": [52, 49], "ts": [56, 53],
        "orb_per": [3, 6], "drb_per": [12, 15], "ast_per": [20, 10],
        "to_per": [14, 16], "min_per": [70, 55], "g": [30, 28], "yr": ["Jr", "So"],
    })
    df.to_csv(tmp_path / "player_2024.csv", index=False)
    players = data_load.load_players(tmp_path)
    assert (players["id_kind"] == "name").all()
    assert players["player_key"].str.startswith("nm:").all()
    assert players["usage"].notna().all() and players["min_pct"].notna().all()


def test_load_teams_computes_adjem(synth_dir):
    teams = data_load.load_teams(synth_dir)
    assert "adjem" in teams.columns
    approx = (teams["adjoe"] - teams["adjde"] - teams["adjem"]).abs().max()
    assert approx < 1e-6

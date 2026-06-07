import numpy as np

from illiniportal import data_load, fit, project
from illiniportal.model import TranslationModel


def test_projection_frame_columns_and_delta(synth_dir):
    players = data_load.load_players(synth_dir)
    teams = data_load.load_teams(synth_dir)
    metrics = ["usage", "ts", "ortg", "ast_pct", "min_pct", "efg",
               "orb_pct", "drb_pct", "to_pct"]
    pre = players[players["year"] == 2024]
    X, meta = project.projection_frame(pre, teams, "illinois", 2025, metrics)
    for m in metrics:
        assert f"{m}_pre" in X.columns
    assert {"delta_L", "usage_pre", "age_proxy_pre", "gp_pre"} <= set(X.columns)
    assert len(X) == len(meta)


def test_score_pool_outputs(synth_dir):
    players = data_load.load_players(synth_dir)
    teams = data_load.load_teams(synth_dir)
    from illiniportal import transfers
    pairs = transfers.attach_team_strength(
        transfers.detect_transfers(players), teams)
    model = TranslationModel().fit(pairs)

    pool = players[(players["year"] == 2024) & (players["min_pct"] >= 40)]
    proj, meta = project.project_players(model, pool, teams, "illinois", 2025)
    board = fit.score_pool(proj, meta)
    assert {"translation_score", "fit_score", "translation_pct",
            "fit_pct"} <= set(board.columns)
    assert board["translation_pct"].between(0, 1).all()
    for s in fit.SKILLS:
        assert f"skill_{s}" in board.columns


def test_need_weights_sum_to_one():
    assert abs(sum(fit.NEED_WEIGHTS.values()) - 1.0) < 1e-6
    assert abs(sum(fit.TRANSLATION_WEIGHTS.values()) - 1.0) < 1e-6

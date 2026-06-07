import numpy as np

from illiniportal import features, transfers


def test_feature_columns_no_duplicates():
    for metric in ["usage", "ortg", "min_pct", "ts"]:
        cols = features.feature_columns(metric)
        assert len(cols) == len(set(cols)), f"dup cols for {metric}"
        assert cols[0] == f"{metric}_pre"
        assert features.LEVEL in cols


def test_usage_pre_not_duplicated_as_control():
    # usage_pre is both the metric's own term and a listed control -> appears once
    cols = features.feature_columns("usage")
    assert cols.count("usage_pre") == 1


def test_build_design_interaction(players_small, teams_small):
    pairs = transfers.attach_team_strength(
        transfers.detect_transfers(players_small), teams_small)
    X, y, df = features.build_design(pairs, "usage")
    assert X.shape[0] == len(y) == 1
    inter = df["usage_pre"].iloc[0] * df["delta_L"].iloc[0]
    assert np.isclose(df["usage_x_dL"].iloc[0], inter)


def test_usable_metrics_threshold(synth_pairs):
    usable = features.usable_metrics(synth_pairs, min_rows=30)
    assert "usage" in usable and "ts" in usable

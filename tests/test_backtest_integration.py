from illiniportal import backtest, data_load, validate


def test_validation_beats_naive(synth_pairs):
    table = validate.evaluate(synth_pairs, cutoff=2024)
    assert not table.empty
    wins = (table["mae_model"] < table["mae_naive"]).sum()
    assert wins >= max(6, len(table) - 1)  # model better on nearly all metrics


def test_transfer_pool_subset(synth_dir, synth_pairs):
    players = data_load.load_players(synth_dir)
    pool = backtest.transfer_pool(players, synth_pairs, 2024)
    assert len(pool) > 0
    assert (pool["year"] == 2024).all()
    # everyone in the pool actually transferred after 2024
    moved = {k.split("pid:")[-1]
             for k in synth_pairs.loc[synth_pairs["year_pre"] == 2024, "player_key"]}
    assert set(pool["pid"].astype(str)) <= moved


def test_separation_monotone_signal(synth_pairs):
    tbl = backtest.separation(synth_pairs, cutoff=2024, n_groups=4)
    assert len(tbl) == 4
    q1 = tbl["mean_actual_production"].iloc[0]
    q4 = tbl["mean_actual_production"].iloc[-1]
    assert q4 > q1                       # top grades out-produce bottom grades
    assert tbl.attrs["spearman"] > 0.1   # positive rank association

"""Phase B: retrospective backtest on Illinois's portal history + target board.

Usage:
    python scripts/backtest.py [--pairs FILE] [--cutoff 2023]
"""

import argparse

import _pathsetup  # noqa: F401

import pandas as pd

from illiniportal import backtest, config, data_load, fit, project
from illiniportal.model import TranslationModel

pd.set_option("display.width", 160)
pd.set_option("display.float_format", "{:.3f}".format)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--cutoff", type=int, default=2023)
    args = ap.parse_args()

    pairs_path = args.pairs or (config.DATA_PROCESSED / "transfer_pairs.parquet")
    pairs = pd.read_parquet(pairs_path)
    players = data_load.load_players()
    teams = data_load.load_teams()

    full_model = TranslationModel().fit(pairs)

    print("\n=== 1. WOULD THE FIT BOARD HAVE FLAGGED THE ACTUAL SIGNINGS? ===")
    print("(rank within that offseason's actual portal pool, projected onto Illinois)")
    print(backtest.flag_signings(full_model, players, teams, pairs)
          .to_string(index=False))

    print("\n=== 2. PROJECTED vs ACTUAL (leave-one-out; the signings translated) ===")
    print(backtest.projected_vs_actual(full_model, pairs, leave_one_out=True)
          .to_string(index=False))

    print(f"\n=== 3. OUT-OF-SAMPLE SEPARATION (train post<={args.cutoff}, "
          f"test after) ===")
    sep = backtest.separation(pairs, cutoff=args.cutoff)
    print(sep.to_string(index=False))
    print(f"Spearman(grade, actual production) on held-out transfers: "
          f"{sep.attrs['spearman']:.3f}")
    print("Top bucket should keep producing; bottom bucket fades (the busts).")

    # Demo target board: the ACTUAL 2026 portal class ranked by fit to Illinois
    # (players with a 2025 season who transferred for 2026) -> site artifact.
    pool = backtest.transfer_pool(players, pairs, 2025)
    proj, meta = project.project_players(full_model, pool, teams,
                                         backtest.ILLINOIS, 2026)
    board = fit.score_pool(proj, meta).sort_values("fit_score", ascending=False)
    out = config.DATA_PROCESSED / "illinois_board_2026.csv"
    board.to_csv(out, index=False)
    cols = ["player", "team", "year", "class", "fit_score", "fit_pct",
            "translation_pct", "proj_usage", "proj_ts", "proj_ast_pct"]
    print(f"\n=== DEMO BOARD: 2026 portal ranked by fit to Illinois "
          f"({len(board)} players) -> {out.name} ===")
    print(board[cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()

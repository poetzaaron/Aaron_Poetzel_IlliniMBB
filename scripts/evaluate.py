"""Out-of-sample validation table: translation model vs naive baseline.

Usage:
    python scripts/evaluate.py [--pairs FILE] [--cutoff 2023]
"""

import argparse

import _pathsetup  # noqa: F401

import pandas as pd

from illiniportal import config, validate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--cutoff", type=int, default=2023,
                    help="train on year_post <= cutoff, test on the rest")
    args = ap.parse_args()

    pairs_path = args.pairs or (config.DATA_PROCESSED / "transfer_pairs.parquet")
    pairs = pd.read_parquet(pairs_path)

    table = validate.evaluate(pairs, cutoff=args.cutoff)
    print(f"\n=== OUT-OF-SAMPLE VALIDATION (train year_post<={args.cutoff}, "
          f"test >{args.cutoff}) ===")
    with pd.option_context("display.float_format", "{:.3f}".format,
                           "display.width", 160):
        print(table.to_string(index=False))

    if not table.empty:
        wins = (table["mae_model"] < table["mae_naive"]).sum()
        print(f"\nmodel beats naive baseline on {wins}/{len(table)} metrics "
              f"(MAE). Positive 'mae_gain_%' = model is better.")


if __name__ == "__main__":
    main()

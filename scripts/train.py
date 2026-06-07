"""Fit the translation model on all transfer pairs; save artifact + coefficients.

Usage:
    python scripts/train.py [--pairs FILE]
"""

import argparse

import _pathsetup  # noqa: F401

import pandas as pd

from illiniportal import config, features
from illiniportal.model import TranslationModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=None)
    args = ap.parse_args()

    pairs_path = args.pairs or (config.DATA_PROCESSED / "transfer_pairs.parquet")
    pairs = pd.read_parquet(pairs_path)

    metrics = features.usable_metrics(pairs)
    print(f"modelling {len(metrics)} metrics: {metrics}")
    model = TranslationModel(metrics=metrics).fit(pairs)

    artifact = config.DATA_PROCESSED / "translation_model.joblib"
    model.save(artifact)

    coefs = model.coefficients()
    coef_path = config.DATA_PROCESSED / "coefficients.csv"
    coefs.to_csv(coef_path, index=False)

    print("\n=== STANDARDISED COEFFICIENTS (level-adjusted regression) ===")
    pivot = coefs[~coefs["feature"].str.startswith("_")].pivot(
        index="feature", columns="metric", values="coef_std")
    with pd.option_context("display.float_format", "{:.3f}".format,
                           "display.width", 160):
        print(pivot.to_string())
    print(f"\nsaved model -> {artifact}\nsaved coefficients -> {coef_path}")


if __name__ == "__main__":
    main()

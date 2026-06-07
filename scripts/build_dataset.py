"""Raw Torvik CSVs -> transfer-pair dataset, with a sanity report.

Usage:
    python scripts/build_dataset.py [--raw DIR] [--out FILE]
"""

import argparse

import _pathsetup  # noqa: F401

import pandas as pd

from illiniportal import config, data_load, transfers

# Known Underwood-era incoming transfers used as a detection sanity check.
KNOWN = [
    ("terrence shannon", "illinois"),  # Torvik spells it "Terrence"
    ("kylan boswell", "illinois"),
    ("andrej stojakovic", "illinois"),
]


def _sanity_report(players, pairs):
    print("\n=== TRANSFER DETECTION SANITY REPORT ===")
    print(f"player-seasons loaded : {len(players):,}")
    print(f"seasons present       : "
          f"{int(players['year'].min())}-{int(players['year'].max())}")
    print(f"transfer pairs found  : {len(pairs):,}")
    print(f"ambiguous name keys   : {pairs.attrs.get('ambiguous_name_keys', 0)}")
    by_id = pairs["id_kind_pre"].value_counts().to_dict()
    print(f"identity source       : {by_id}")
    print("pairs by post-season  :")
    print(pairs["year_post"].value_counts().sort_index().to_string())

    print("\nknown-transfer checks (should be FOUND):")
    pk = pairs.assign(_nm=pairs["player_pre"].map(data_load.name_key),
                      _to=pairs["team_key_post"])
    for name, dest in KNOWN:
        hit = pk[(pk["_nm"].str.contains(name, na=False))
                 & (pk["_to"].str.contains(dest, na=False))]
        flag = "FOUND" if len(hit) else "missing"
        extra = ""
        if len(hit):
            r = hit.iloc[0]
            extra = f"  ({r['team_pre']} {r['year_pre']} -> {r['team_post']} {r['year_post']})"
        print(f"  [{flag:7}] {name} -> {dest}{extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=None, help="raw CSV dir (default data/raw)")
    ap.add_argument("--out", default=None, help="output parquet path")
    args = ap.parse_args()

    players = data_load.load_players(args.raw)
    teams = data_load.load_teams(args.raw)

    pairs = transfers.detect_transfers(players)
    pairs = transfers.attach_team_strength(pairs, teams)

    _sanity_report(players, pairs)

    out = args.out or (config.DATA_PROCESSED / "transfer_pairs.parquet")
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(out, index=False)
    print(f"\nwrote {len(pairs):,} pairs -> {out}")


if __name__ == "__main__":
    main()

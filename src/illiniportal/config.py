"""Paths, schema, column aliases, and modelling constants.

Torvik labels a season by its *ending* year: ``2024`` == the 2023-24 season.
The loader is alias-driven (see :func:`canonical_name`) so it adapts to whatever
exact header spellings the committed Torvik exports use.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

YEAR_MIN = 2022
YEAR_MAX = 2026
COVID_YEARS = {2021}  # 2020-21 season; minutes/usage distorted (outside range)

# --- canonical schemas -------------------------------------------------------
PLAYER_CANONICAL = [
    "player", "pid", "team", "conf", "year",
    "gp", "min_pct", "usage", "ortg", "efg", "ts",
    "orb_pct", "drb_pct", "ast_pct", "to_pct",
    "class", "position", "height", "obpm", "dbpm", "bpm", "pts",
    # pillar-screen stats (Stage 1)
    "ft_pct", "two_pct", "tpm", "tpa", "three_pct", "blk_pct", "stl_pct",
    "rim_pct", "mid_pct",
    "oreb_pg", "dreb_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "pts_pg",
]
TEAM_CANONICAL = ["team", "conf", "year", "adjoe", "adjde", "barthag", "sos"]

# Torvik player advanced export is HEADERLESS/positional. Verified column index
# -> canonical (see player_2024.csv; indices confirmed across 2022-2026). Used
# when a file has no recognisable header. Indices 13-64 surface the pillar-screen
# stats the translation model itself does not use (shooting/finishing/defense/role).
POSITIONAL_PLAYER = {
    0: "player", 1: "team", 2: "conf", 3: "gp", 4: "min_pct", 5: "ortg",
    6: "usage", 7: "efg", 8: "ts", 9: "orb_pct", 10: "drb_pct",
    11: "ast_pct", 12: "to_pct",
    15: "ft_pct", 18: "two_pct", 19: "tpm", 20: "tpa", 21: "three_pct",
    22: "blk_pct", 23: "stl_pct",
    25: "class", 26: "height", 31: "year", 32: "pid",
    40: "rim_pct", 41: "mid_pct",
    57: "oreb_pg", 58: "dreb_pg", 59: "reb_pg", 60: "ast_pg", 61: "stl_pg",
    62: "blk_pg", 63: "pts_pg", 64: "position",
}

# Shooting/finishing percentages that Torvik stores as 0-1 decimals (FT/2P/3P/
# rim/mid). The loader rescales these to the 0-100 scale the other rate stats use,
# but only when the column actually looks like a 0-1 fraction (header exports may
# already be 0-100), so the rescale is safe either way.
PCT01_COLS = ["ft_pct", "two_pct", "three_pct", "rim_pct", "mid_pct"]

# Globs for locating each export inside the raw dir.
PLAYER_GLOBS = ["player*.csv", "*player*.csv"]
TEAM_GLOBS = ["*team*results*.csv", "team*.csv", "*team_ratings*.csv"]

# Stats the translation model predicts. A metric is used only if present in the
# loaded data for both the pre- and post-transfer season.
METRICS = [
    "usage", "ortg", "efg", "ts",
    "orb_pct", "drb_pct", "ast_pct", "to_pct", "min_pct",
]

# Controls added to every per-metric regression (the Z vector). All are
# pre-transfer values (what you know before signing the player).
CONTROLS = ["usage_pre", "min_pct_pre", "age_proxy_pre", "gp_pre"]

# Class/experience -> years-of-experience proxy (Underwood up-weights experience).
CLASS_TO_YEARS = {
    "fr": 0, "freshman": 0,
    "so": 1, "sophomore": 1,
    "jr": 2, "junior": 2,
    "sr": 3, "senior": 3,
    "gr": 4, "grad": 4, "graduate": 4, "5y": 4, "5th": 4,
}

# --- pillar screen (Stage 1) -------------------------------------------------
# Torvik role label -> coarse position group used for height/skill percentiles.
POSITION_GROUPS = {
    "pure pg": "G", "scoring pg": "G", "combo g": "G", "wing g": "G",
    "wing f": "W",
    "stretch 4": "B", "pf/c": "B", "c": "B",
}
GROUP_LABELS = {"G": "Guard", "W": "Wing", "B": "Big"}


def position_group(label, height_in=None):
    """Coarse {G,W,B} group from a Torvik role label, height as a fallback."""
    key = str(label).strip().lower()
    if key in POSITION_GROUPS:
        return POSITION_GROUPS[key]
    if height_in is not None and height_in == height_in:  # not NaN
        if height_in < 76:        # below 6-4
            return "G"
        if height_in < 80:        # 6-4 .. 6-7
            return "W"
        return "B"
    return None


# Screening thresholds. Floors and flags, NOT a weighted average; one strength
# cannot offset a disqualifying weakness. All overridable from the UI; shooting is
# weighted hardest (the canonical disqualifier). Percentile floors are taken within
# a player's position group against the full D1 season population.
PILLAR_DEFAULTS = {
    # positional size: height percentile within position group
    "size_pctile_flag": 20.0,
    "size_pctile_warn": 35.0,
    # shooting (0-100 scale): a genuine non-shooter trips multiple of these
    "shoot_ts_floor": 50.0,         # true shooting
    "shoot_three_floor": 30.0,      # 3P% ...
    "shoot_three_min_att": 40,      # ... judged only at this 3PA volume
    "shoot_ft_floor": 62.0,         # FT% as a touch/feel proxy
    # other skills: percentile-within-position floors
    "skill_pctile_flag": 15.0,
    "skill_pctile_warn": 30.0,
    # basketball-IQ proxy: assist-to-turnover ratio, ranked WITHIN position (a flat
    # ratio floor would unfairly flag bigs, who carry low AST:TO by role).
    "iq_pctile_flag": 15.0,
    "iq_pctile_warn": 30.0,
}

# --- header alias map --------------------------------------------------------
# Keys are normalised (lowercase, alphanumerics only); values are canonical.
_RAW_ALIASES = {
    # identity
    "player": "player", "playername": "player", "name": "player", "fullname": "player",
    "pid": "pid", "playerid": "pid", "id": "pid",
    "team": "team", "school": "team",
    "conf": "conf", "conference": "conf",
    "year": "year", "season": "year", "yearno": "year",
    # volume / rate
    "gp": "gp", "g": "gp", "games": "gp", "gamesplayed": "gp",
    "minpct": "min_pct", "minper": "min_pct", "minutespct": "min_pct", "mins": "min_pct",
    "usage": "usage", "usg": "usage", "usgpct": "usage", "usagerate": "usage", "usg5": "usage",
    "ortg": "ortg", "offrtg": "ortg", "offensiverating": "ortg",
    "efg": "efg", "efgpct": "efg", "efgper": "efg",
    "ts": "ts", "tspct": "ts", "tsper": "ts", "trueshooting": "ts",
    "orbpct": "orb_pct", "orper": "orb_pct", "orbper": "orb_pct", "orebpct": "orb_pct", "oreb": "orb_pct",
    "drbpct": "drb_pct", "drper": "drb_pct", "drbper": "drb_pct", "drebpct": "drb_pct", "dreb": "drb_pct",
    "astpct": "ast_pct", "astper": "ast_pct", "assistpct": "ast_pct",
    "topct": "to_pct", "toper": "to_pct", "tovpct": "to_pct", "turnoverpct": "to_pct",
    # bio
    "class": "class", "yr": "class", "exp": "class", "experience": "class",
    "position": "position", "pos": "position", "role": "position",
    "height": "height", "ht": "height",
    "obpm": "obpm", "dbpm": "dbpm", "bpm": "bpm",
    "pts": "pts", "points": "pts", "ppg": "pts",
    # pillar-screen stats
    "ftpct": "ft_pct", "ftper": "ft_pct",
    "2ppct": "two_pct", "twoppct": "two_pct", "2pper": "two_pct",
    "3pm": "tpm", "threepm": "tpm", "3pa": "tpa", "threepa": "tpa",
    "3ppct": "three_pct", "threeppct": "three_pct", "3pper": "three_pct",
    "blkpct": "blk_pct", "blockpct": "blk_pct",
    "stlpct": "stl_pct", "stealpct": "stl_pct",
    "rimpct": "rim_pct", "midpct": "mid_pct", "midrangepct": "mid_pct",
    "orebpg": "oreb_pg", "drebpg": "dreb_pg", "rebpg": "reb_pg",
    "astpg": "ast_pg", "stlpg": "stl_pg", "blkpg": "blk_pg", "ptspg": "pts_pg",
    # team ratings
    "adjoe": "adjoe", "adjo": "adjoe", "adjoff": "adjoe", "adjoffeff": "adjoe",
    "adjde": "adjde", "adjd": "adjde", "adjdef": "adjde", "adjdefeff": "adjde",
    "barthag": "barthag", "bart": "barthag",
    "sos": "sos", "strengthofschedule": "sos",
}


def _norm(s) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def canonical_name(raw):
    """Map a raw header to its canonical name, or ``None`` if unknown."""
    return _RAW_ALIASES.get(_norm(raw))

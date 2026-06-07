"""Stage-1 pillar screen: floors and flags, shooting as the hard disqualifier."""

import numpy as np
import pandas as pd

from illiniportal import pillars


def _guard(pid, height_in, *, ts=56, three=36, ft=78, tpa=120, ast=18, to=12,
           rim=55, orb=3, drb=10, stl=2, blk=0.5):
    return dict(pid=str(pid), pos_group="G", height=f"6-{height_in - 72}",
                height_in=float(height_in), ts=ts, three_pct=three, ft_pct=ft,
                tpa=tpa, ast_pct=ast, to_pct=to, rim_pct=rim, orb_pct=orb,
                drb_pct=drb, stl_pct=stl, blk_pct=blk)


def _reference(n=40):
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n):
        rows.append(_guard(1000 + i, height_in=int(73 + (i % 8)),
                           ts=float(rng.uniform(52, 60)),
                           three=float(rng.uniform(33, 39)),
                           ast=18, to=14, rim=55, orb=3, drb=10, stl=2, blk=0.5))
    return pd.DataFrame(rows)


def _status(df, pid, col):
    return df.loc[df["pid"] == str(pid), col].iloc[0]


def test_short_guard_flags_size_only():
    ref = _reference()
    pool = pd.DataFrame([_guard(1, height_in=70)])   # shorter than the field
    out = pillars.pillar_status(pool, ref)
    assert _status(out, 1, "size_status") == "flag"
    assert _status(out, 1, "skill_status") == "pass"
    assert bool(_status(out, 1, "pillar_flag")) is True


def test_non_shooter_trips_skill_via_shooting():
    ref = _reference()
    # tall enough (size pass), but a genuine non-shooter on volume
    pool = pd.DataFrame([_guard(2, height_in=78, ts=45, three=24, ft=55, tpa=100)])
    out = pillars.pillar_status(pool, ref)
    assert _status(out, 2, "shooting_status") == "flag"
    assert _status(out, 2, "skill_status") == "flag"      # shooting is the disqualifier
    assert _status(out, 2, "size_status") == "pass"
    assert bool(_status(out, 2, "pillar_flag")) is True


def test_clean_guard_clears_all_gates():
    ref = _reference()
    pool = pd.DataFrame([_guard(3, height_in=77, ts=60, three=40, ft=85, tpa=150,
                                ast=22, to=11, rim=58, drb=11, stl=3)])
    out = pillars.pillar_status(pool, ref)
    assert _status(out, 3, "size_status") == "pass"
    assert _status(out, 3, "skill_status") == "pass"
    assert _status(out, 3, "iq_status") == "pass"
    assert bool(_status(out, 3, "pillar_flag")) is False


def test_single_nonshooting_weakness_warns_not_flags():
    """One strength can't offset a *disqualifying* weakness, but a lone non-shooting
    deficiency demotes to warn, it does not hard-flag (shooting is the disqualifier)."""
    ref = _reference()
    # elite shooter, but bottom-of-position rebounding only (one weak skill)
    pool = pd.DataFrame([_guard(4, height_in=77, ts=61, three=41, ft=86,
                                orb=0.1, drb=1.0)])
    out = pillars.pillar_status(pool, ref)
    assert _status(out, 4, "shooting_status") == "pass"
    assert _status(out, 4, "skill_status") in ("warn", "pass")
    assert bool(_status(out, 4, "pillar_flag")) is False


def test_character_manual_and_fouling_blocked():
    ref = _reference()
    out = pillars.pillar_status(pd.DataFrame([_guard(5, height_in=76)]), ref)
    assert _status(out, 5, "character_status") == "manual"
    assert _status(out, 5, "fouling_status") == "blocked"   # data-blocked, not dropped

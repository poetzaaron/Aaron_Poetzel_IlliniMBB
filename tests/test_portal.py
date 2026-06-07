import pandas as pd

from illiniportal import portal


def _players():
    rows = [
        ("John Blackwell", "Wisconsin", "1", 80.0, 2026),
        ("Jayden Williams", "Dartmouth", "2", 70.0, 2026),   # homonym, higher min
        ("Jayden Williams", "Bucknell", "3", 40.0, 2026),    # homonym, lower min
        ("Michael Nwoko", "LSU", "4", 60.0, 2026),
        ("Old Timer", "Duke", "5", 90.0, 2025),              # wrong season, ignored
    ]
    return pd.DataFrame(rows, columns=["player", "team", "pid", "min_pct", "year"])


def test_forward_pool_matching():
    portal_df = pd.DataFrame({"player": [
        "John Blackwell",   # unique name match
        "Jayden Williams",  # ambiguous -> highest minutes (Dartmouth)
        "Mike Nwoko",       # first-name variant -> Michael Nwoko
        "Ghost Player",     # unmatched
    ]})
    pool, report = portal.forward_pool(_players(), portal_df)

    assert report["matched"] == 3
    assert "Jayden Williams" in report["ambiguous"]
    assert "Ghost Player" in report["unmatched"]
    # homonym resolved to the higher-minutes player
    jw = pool[pool["player"] == "Jayden Williams"].iloc[0]
    assert jw["team"] == "Dartmouth"
    # variant recovery
    assert (pool["player"] == "Michael Nwoko").any()


def test_load_portal_names_only(tmp_path):
    p = tmp_path / "portal_2026.csv"
    p.write_text("player\nJohn Blackwell\nPJ Haggerty\n")
    df = portal.load_portal(p)
    assert list(df["player"]) == ["John Blackwell", "PJ Haggerty"]


def test_find_portal_file_skips_template(tmp_path):
    (tmp_path / "portal_2026.template.csv").write_text("player\nX\n")
    (tmp_path / "portal_2026.csv").write_text("player\nY\n")
    found = portal.find_portal_file(tmp_path)
    assert found.name == "portal_2026.csv"

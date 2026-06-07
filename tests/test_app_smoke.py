"""Smoke test: the War Room app runs end-to-end with no uncaught exceptions."""

import pytest

pytest.importorskip("streamlit")

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_app_runs_clean():
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert [t.label for t in at.tabs] == ["Overview", "Players"]
    assert len(at.button) > 0          # master-row buttons rendered
    assert len(at.dataframe) >= 3
    assert at.session_state["sel_pid"]      # a player is selected by default


def test_app_pillar_gate_toggle():
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    assert not at.exception
    # hard-apply the Stage-1 gates -> board still renders, no error
    at.toggle[0].set_value(True)
    at.run()
    assert not at.exception


def test_app_filter_and_rowclick():
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    # click a master row -> selection updates, no error
    at.button[2].click()
    at.run()
    assert not at.exception
    assert at.session_state["sel_pid"]
    # crank a need weight -> re-ranks without error
    at.sidebar.slider[0].set_value(90)
    at.run()
    assert not at.exception
    # switch to a backtest cycle
    at.sidebar.selectbox[0].set_value("2024-25")
    at.run()
    assert not at.exception

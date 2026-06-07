"""IlliniPortal: transfer-portal translation and fit terminal.

Forward 2026-27 portal board (ingests data/raw/portal_2026.csv) plus retrospective
cycles, a translation/fit explainer, and the out-of-sample backtest. Run:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(HERE), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import altair as alt
import pandas as pd
import streamlit as st

import theme
from illiniportal import (backtest, config, data_load, fit, pillars, portal,
                          project, transfers, validate)
from illiniportal.model import TranslationModel

st.set_page_config(page_title="IlliniPortal", page_icon="🟧", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(theme.CSS, unsafe_allow_html=True)
theme.register_altair_theme()

FORWARD = "2026-27"
CYCLE_MAP = {"2025-26": (2025, 2026), "2024-25": (2024, 2025),
             "2023-24": (2023, 2024), "2022-23": (2022, 2023)}
CYCLES = [FORWARD] + list(CYCLE_MAP)
SEASON_LABEL = {2026: "2025-26", 2025: "2024-25", 2024: "2023-24",
                2023: "2022-23", 2022: "2021-22"}
SKILL_ORDER = list(fit.SKILLS.keys())
CLASS_MIN = {"Any": -1, "Sophomore+": 1, "Junior+": 2, "Senior / grad": 3}
# guard height floor (opening default 6-3; Illinois targets big guards)
HEIGHT_FLOORS = {"None": None, "6-1": 73, "6-2": 74, "6-3": 75, "6-4": 76, "6-5": 77}
GROUP_FROM_LABEL = {v: k for k, v in config.GROUP_LABELS.items()}


# ----------------------------------------------------------------- engine (cached)
@st.cache_data(show_spinner=False)
def frames():
    return data_load.load_players(), data_load.load_teams()


@st.cache_data(show_spinner=False)
def pairs():
    p, t = frames()
    return transfers.attach_team_strength(transfers.detect_transfers(p), t)


@st.cache_resource(show_spinner=False)
def model():
    return TranslationModel().fit(pairs())


@st.cache_data(show_spinner=False)
def build_cycle(cycle: str):
    """Return (proj, meta, info) for a cycle. Forward = 2026-27 portal."""
    p, t = frames()
    mdl = model()
    if cycle == FORWARD:
        pfile = portal.find_portal_file(data_load.config.DATA_RAW)
        if pfile is None:
            return None, None, {"empty": True, "report": None}
        pool, report = portal.forward_pool(p, portal.load_portal(pfile))
        pre_year, dest_year = 2026, 2026
        pre_label, dest_label = "2025-26", "2026-27"
        signed_map = dict(zip(pool["pid"].astype(str), pool["committed_to"]))
    else:
        pre_year, dest_year = CYCLE_MAP[cycle]
        pool = backtest.transfer_pool(p, pairs(), pre_year)
        report = None
        pre_label, dest_label = SEASON_LABEL[dest_year - 1], SEASON_LABEL[dest_year]
        pr = pairs()
        pr = pr[pr["year_pre"] == pre_year]
        signed_map = {k.split("pid:")[-1]: v
                      for k, v in zip(pr["player_key"], pr["team_post"])}

    X, meta = project.projection_frame(pool, t, "illinois", dest_year, mdl.metrics)
    proj = project.project(mdl, X)
    for m in mdl.metrics:
        meta[f"pre_{m}"] = X[f"{m}_pre"].values
    meta["signed"] = meta["pid"].astype(str).map(signed_map).fillna("")
    info = {"empty": False, "report": report, "pre_label": pre_label,
            "dest_label": dest_label, "pre_year": pre_year,
            "pool": pool.reset_index(drop=True)}
    return proj.reset_index(drop=True), meta.reset_index(drop=True), info


@st.cache_data(show_spinner=False)
def default_rank(cycle: str):
    proj, meta, info = build_cycle(cycle)
    if proj is None:
        return {}
    b = fit.score_pool(proj, meta).dropna(subset=["fit_score"])
    b = b.sort_values("fit_score", ascending=False).reset_index(drop=True)
    return {str(pid): i + 1 for i, pid in enumerate(b["pid"])}


@st.cache_data(show_spinner=False)
def validation_table():
    return validate.evaluate(pairs(), cutoff=2023)


@st.cache_data(show_spinner=False)
def mae_by_metric():
    """Per-metric out-of-sample MAE: the half-width of a projection's likely range."""
    vt = validation_table()
    return dict(zip(vt["metric"], vt["mae_model"]))


@st.cache_data(show_spinner=False)
def separation_table():
    return backtest.separation(pairs(), cutoff=2023)


@st.cache_data(show_spinner=False)
def signings_table():
    p, t = frames()
    return backtest.flag_signings(model(), p, t, pairs())


@st.cache_data(show_spinner=False)
def reference_pool(pre_year: int):
    """Full D1 season population for within-position pillar percentiles."""
    p, _ = frames()
    return p[p["year"] == pre_year].copy()


@st.cache_data(show_spinner=False)
def pillar_hits():
    """Run the pillar screen on Underwood's known signings (pre-transfer season)."""
    p, _ = frames()
    rows = []
    for name, team, pre_year, dest_year in backtest.SIGNINGS:
        player = backtest._find(p, name, team, pre_year)
        if player is None:
            continue
        ps = pillars.pillar_status(player.to_frame().T, reference_pool(pre_year))
        r = ps.iloc[0]
        rows.append({"player": f"{name} · {team} {pre_year}",
                     "size": r["size_status"], "skill": r["skill_status"],
                     "IQ": r["iq_status"], "character": r["character_status"],
                     "fouling": r["fouling_status"],
                     "verdict": "clears active gates" if not r["pillar_flag"]
                     else r["pillar_summary"]})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def pillar_flagged(pre_year: int = 2025, n: int = 6):
    """A few entrants the screen flags, with the specific failing pillar."""
    p, _ = frames()
    pool = backtest.transfer_pool(p, pairs(), pre_year)
    ps = pillars.pillar_status(pool.reset_index(drop=True), reference_pool(pre_year))
    j = pool.reset_index(drop=True)[["player", "team", "position"]].join(ps)
    flagged = j[j["pillar_flag"]].copy()
    flagged["flagged_on"] = flagged["pillar_summary"]
    cols = ["player", "team", "position", "flagged_on", "skill_reason"]
    return flagged[cols].head(n).reset_index(drop=True)


# ----------------------------------------------------------------- helpers
def archetype(r):
    if r.get("proj_drb_pct", 0) >= 18 or r.get("proj_orb_pct", 0) >= 8:
        return "Big"
    if r.get("proj_ast_pct", 0) >= 18:
        return "Guard"
    return "Wing"


def class_label(age):
    return {0: "Fr", 1: "So", 2: "Jr", 3: "Sr", 4: "Gr"}.get(int(age), "n/a") \
        if pd.notna(age) else "n/a"


def pct_of(series, value, invert=False):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty or pd.isna(value):
        return 0.0
    return float((s.gt(value).mean() if invert else s.lt(value).mean()) * 100)


def fmt(v, d=0):
    try:
        if v is None or pd.isna(v):
            return "n/a"
    except (TypeError, ValueError):
        return "n/a"
    return f"{float(v):.{d}f}"


def arrow(move):
    return "▲" if move >= 2 else ("▼" if move <= -2 else "·")


def set_sel(pid):
    st.session_state["sel_pid"] = str(pid)


# ----------------------------------------------------------------- sidebar
for s in SKILL_ORDER:
    st.session_state.setdefault(f"w_{s}", int(round(fit.NEED_WEIGHTS[s] * 100)))
st.session_state.setdefault("w_exp", float(fit.EXPERIENCE_WEIGHT))


with st.sidebar:
    st.markdown('<div class="sbh">Illini<em>Portal</em></div>', unsafe_allow_html=True)
    st.markdown('<div class="sbk">Cycle</div>', unsafe_allow_html=True)
    cycle = st.selectbox("Cycle", CYCLES, index=0, label_visibility="collapsed",
                         format_func=lambda c: (f"{c}  ·  live portal" if c == FORWARD
                                                else f"{c}  ·  backtest"))

    st.markdown('<div class="sbk">Pre-ranking filters · defaults</div>',
                unsafe_allow_html=True)
    st.caption("Opening defaults reflect the backcourt void. Fully overridable.")
    positions = st.multiselect("Position", ["Guard", "Wing", "Big"],
                               default=["Guard", "Wing"])
    guard_floor_lbl = st.selectbox("Guard height floor", list(HEIGHT_FLOORS), index=3)
    exp_min = st.selectbox("Minimum experience (soft)", list(CLASS_MIN), index=0)
    st.caption("Experience is already inside the fit score; this only narrows the view.")

    st.markdown('<div class="sbk">Need vector · weights</div>', unsafe_allow_html=True)
    st.caption("0–100 relative weights; only the proportions matter (normalised to "
               "100%). Higher = Illinois values that skill more. Weights re-rank.")
    for s in SKILL_ORDER:
        st.slider(theme.SKILL_LABELS[s], 0, 100, key=f"w_{s}")
    st.slider("Experience emphasis", 0.0, 0.8, key="w_exp", step=0.05)

    st.markdown('<div class="sbk">Stage-1 pillar gates</div>', unsafe_allow_html=True)
    hard_gates = st.toggle("Hard-apply gates (hide flagged)", value=False,
                           help="Off: flagged players stay visible but demoted. "
                                "On: Stage 1 removes gate-failures from the board.")
    with st.expander("Gate thresholds"):
        size_flag = st.slider("Size: flag below height %ile", 0, 50,
                              int(config.PILLAR_DEFAULTS["size_pctile_flag"]))
        ts_floor = st.slider("Shooting: TS% floor", 40, 60,
                             int(config.PILLAR_DEFAULTS["shoot_ts_floor"]))
        three_floor = st.slider("Shooting: 3P% floor", 20, 40,
                                int(config.PILLAR_DEFAULTS["shoot_three_floor"]))
        iq_flag = st.slider("IQ: flag below AST:TO %ile (within position)", 0, 40,
                            int(config.PILLAR_DEFAULTS["iq_pctile_flag"]))
    ui_thresholds = {"size_pctile_flag": size_flag, "shoot_ts_floor": ts_floor,
                     "shoot_three_floor": three_floor, "iq_pctile_flag": iq_flag}

    st.markdown('<div class="sbk">View</div>', unsafe_allow_html=True)
    top_n = st.slider("Rows shown", 10, 60, 30, 5)
    search = st.text_input("Search player", "")
    guard_floor = HEIGHT_FLOORS[guard_floor_lbl]

raw_w = {s: st.session_state[f"w_{s}"] for s in SKILL_ORDER}
tot = sum(raw_w.values()) or 1
need_weights = {k: v / tot for k, v in raw_w.items()}
exp_w = st.session_state["w_exp"]

# ----------------------------------------------------------------- compute board
proj, meta, info = build_cycle(cycle)
board = view = None
if proj is not None:
    board = fit.score_pool(proj, meta, need_weights=need_weights, experience_weight=exp_w)
    board = board.dropna(subset=["fit_score"]).copy()
    board["archetype"] = board.apply(archetype, axis=1)
    board["class_lbl"] = board["age_proxy"].map(class_label)
    board["pos_lbl"] = board["pos_group"].map(config.GROUP_LABELS).fillna("n/a")

    # Stage 1: the pillar screen sets ELIGIBILITY; it never touches fit_score.
    pstat = pillars.pillar_status(info["pool"], reference_pool(info["pre_year"]),
                                  thresholds=ui_thresholds)
    board = board.drop(columns=[c for c in pstat.columns if c != "pid"
                                and c in board.columns], errors="ignore")
    board = board.merge(pstat, on="pid", how="left")
    board["pillar_flag"] = board["pillar_flag"].fillna(False)

    # Rank by fit (weights only) for the ▲/▼ arrows, THEN demote flagged players
    # for display order; a flagged player's score is identical, only its row moves.
    board = board.sort_values("fit_score", ascending=False).reset_index(drop=True)
    board["fit_rank"] = board.index + 1
    drank = default_rank(cycle)
    board["move"] = [drank.get(str(pid), fr) - fr
                     for pid, fr in zip(board["pid"], board["fit_rank"])]
    board = board.sort_values(["pillar_flag", "fit_score"],
                              ascending=[True, False]).reset_index(drop=True)

    pos_codes = ({GROUP_FROM_LABEL[p] for p in positions} if positions
                 else set(config.GROUP_LABELS))
    view = board[board["pos_group"].isin(pos_codes)
                 & (board["age_proxy"] >= CLASS_MIN[exp_min])]
    if guard_floor is not None:
        view = view[~((view["pos_group"] == "G") & (view["height_in"] < guard_floor))]
    if hard_gates:
        view = view[~view["pillar_flag"]]
    if search.strip():
        view = view[view["player"].str.contains(search.strip(), case=False, na=False)]
    view = view.reset_index(drop=True)

# status bar
pool_n = 0 if board is None else len(board)
matched_cell = ""
if cycle == FORWARD and info.get("report"):
    matched_cell = f"{info['report']['matched']}/{info['report']['total']}"
flagged_n = 0 if board is None else int(board["pillar_flag"].sum())
cells = [("Cycle", cycle, True), ("Pool", str(pool_n), False),
         ("Screen", f"{flagged_n}/{pool_n} flagged{' · gated' if hard_gates else ''}", False),
         ("Experience w", f"{exp_w:.2f}", False)]
if matched_cell:
    cells.append(("Portal matched", matched_cell, False))
st.markdown(theme.status_bar(cells, "● LIVE PORTAL" if cycle == FORWARD else "BACKTEST"),
            unsafe_allow_html=True)

tab_over, tab_war = st.tabs(["Overview", "Players"])

# ============================================================ OVERVIEW · WHAT THIS IS
with tab_over, st.container(key="ov_what"):
    st.markdown('<div class="kick"><div class="b"></div>'
                '<div class="t">What this is</div></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lede">This is a portal-evaluation terminal for Illinois basketball. '
        'It answers one question for the GM: <b>when a transfer jumps competition '
        'levels, how much of their production actually comes with them, and does '
        'their surviving profile fill an Illinois need?</b></div>', unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns(2)
    c1.markdown("""
<div class="panelbox acc">
  <h4>1 · The translation model</h4>
  <p>For each rate stat we learned, across all of D1, how production changes when
  a player switches schools, keyed on the <b>level jump ΔL</b> (destination minus
  origin team strength, adjEM). A ridge regression per stat:</p>
  <div class="eq">stat_post = b0 + b1·stat_pre + b2·ΔL + b3·(stat_pre×ΔL) + controls</div>
  <p class="cap">Per player: take their pre-portal season, measure the jump to
  Illinois, and project each rate (usage, TS%, AST%, reb%, TO%, minutes).</p>
</div>""", unsafe_allow_html=True)
    c2.markdown("""
<div class="panelbox">
  <h4>2 · Two scores</h4>
  <p><b>Translation score</b>: will this profile keep <i>producing</i> at the new
  level?</p>
  <p><b>Fit score</b> re-weights the projected skills by <i>Illinois's</i> need
  vector, plus an explicit experience bonus (Underwood signs experienced portal
  players). The sidebar sliders <i>are</i> this weighting; move them and the board
  re-ranks.</p>
  <ol class="steps">
    <li data-n="i">Project the player's stats onto Illinois.</li>
    <li data-n="ii">Roll projected stats into seven standardised skills.</li>
    <li data-n="iii">Weight by need + experience → fit.</li>
  </ol>
</div>""", unsafe_allow_html=True)

    st.markdown(theme.kicker("Translation accuracy",
                "out-of-sample · model vs naive baseline"), unsafe_allow_html=True)
    st.markdown('<div class="note">How well that regression actually translates '
                'production, tested out-of-sample (trained on 2023, tested on later '
                'transfers) against a naive "stats carry over unchanged" baseline. The '
                'naive R² is negative, so raw pre-transfer numbers do not survive the jump; '
                'the model captures the level-adjusted regression to the mean.</div>',
                unsafe_allow_html=True)
    st.write("")
    vt = validation_table()[["metric", "n_test", "mae_model", "mae_naive",
                             "r2_model", "r2_naive", "mae_gain_%"]]
    st.dataframe(vt, hide_index=True, width='stretch', column_config={
        "mae_model": st.column_config.NumberColumn("MAE model", format="%.2f"),
        "mae_naive": st.column_config.NumberColumn("MAE naive", format="%.2f"),
        "r2_model": st.column_config.NumberColumn("R² model", format="%.2f"),
        "r2_naive": st.column_config.NumberColumn("R² naive", format="%.2f"),
        "mae_gain_%": st.column_config.NumberColumn("MAE gain %", format="%.0f")})

    st.markdown(theme.kicker("How the level jump (ΔL) is calculated"),
                unsafe_allow_html=True)
    st.markdown("""
<div class="panelbox acc">
  <p>Every projection is based on <b>ΔL, the change in competition level</b> between
  the player's old team and the destination:</p>
  <div class="eq">ΔL = adjEM(destination) − adjEM(origin)</div>
  <p><b>adjEM</b> (adjusted efficiency margin) = a team's <b>adjusted offensive
  efficiency − adjusted defensive efficiency</b>, from Torvik's tempo-free team
  ratings (points per 100 possessions vs. an average D1 opponent). A <b>positive ΔL</b>
  means stepping <i>up</i> to a stronger program; negative means stepping down. The
  model learned, across all of D1, how each rate stat regresses as ΔL grows, which is
  why a high-usage mid-major scorer is projected to shed more usage moving up than a
  role player does. For the live board the destination is Illinois's <b>2025-26 adjEM</b>
  (the labeled proxy for 2026-27), so a Providence guard, for example, shows a large positive ΔL.</p>
  <p class="cap">Note: ΔL (the team-level jump) is distinct from the <b>translation
  grade</b> in the validation section above. That grade is the projected-production
  composite for the player, not the level jump.</p>
</div>""", unsafe_allow_html=True)

# ============================================================ OVERVIEW · ROSTER & DEFAULTS
with tab_over, st.container(key="ov_roster"):
    st.markdown(theme.kicker("Illinois 2026-27 roster context",
                "informational · sets board's defaults"),
                unsafe_allow_html=True)
    st.markdown(
        '<div class="lede">The state of the program that the transfer board is built around. The current '
        'backcourt void is why the board opens on <b>guard / wing, 6-3+</b> and '
        'the need vector tilts to <b>shooting, creation and efficiency</b> (with '
        'experience up-weighted in the fit score). None of this changes how a player is '
        '<i>scored</i>; it only sets where the board starts.</div>', unsafe_allow_html=True)
    st.write("")

    st.markdown(
        '<div class="panelbox acc"><h4>The screen runs four of five pillars</h4>'
        '<p>The first screen gates every player on <b>positional size</b>, <b>skill '
        'deficiencies</b>, <b>basketball IQ</b> (AST:TO) and <b>character</b> '
        '(a manual flag that can be set). The fifth framework pillar, <b>defensive fouling '
        'discipline</b>, is <b>not available right now</b>: the Torvik export carries '
        'no fouls-committed or opponent-free-throw-rate field, so we cannot compute it '
        'at the moment. It can be added pending a data re-pull.</p></div>', unsafe_allow_html=True)
    st.write("")

    rc1, rc2, rc3 = st.columns(3)
    rc1.markdown(
        '<div class="panelbox"><h4>Returning core</h4>'
        '<p>Five of the top-eight scorers from the Final Four team are back.</p>'
        '<p class="cap">Andrej Stojakovic · Tomislav Ivisic · Zvonimir Ivisic · '
        'David Mirkovic · Jake Davis</p>'
        '<p>Frontcourt size and rebounding are largely covered, which is why '
        'the need vector does not prioritize rebounding.</p></div>', unsafe_allow_html=True)
    rc2.markdown(
        '<div class="panelbox"><h4>Departing · the gap left</h4>'
        '<p><b>Keaton Wagler</b>, Big Ten Freshman of the Year, 6-6 lead scorer, '
        'projected top NBA pick. His departure costs primary perimeter scoring and creation.</p>'
        '<p><b>Kylan Boswell</b>, senior lead guard, eligibility exhausted. The loss here is '
        'on-ball creation and leadership.</p>'
        '<p class="cap">Depth out: Humrichous, Redd (graduation); Petrovic, Bilic, '
        'Rodgers, Lee (portal).</p></div>', unsafe_allow_html=True)
    rc3.markdown(
        '<div class="panelbox"><h4>Incoming · committed</h4>'
        '<p><b>Stefan Vaaks</b>, 6-7 guard/wing, Providence transfer.</p>'
        '<p class="cap">Freshmen: Quentin Coleman · Lucas Morillo · Ethan Brown · '
        'Landon Davis · Zavier Zens</p></div>', unsafe_allow_html=True)

    st.markdown(theme.kicker("Illinois's assumed need vector",
                "editable · the default slider weights"), unsafe_allow_html=True)
    st.markdown('<div class="note">The sidebar sliders are a <b>0–100 relative weight</b> '
                'per skill. Only the <b>proportions</b> matter: they are normalised to '
                'sum to 100%, so a slider at 30 with the rest at 10 means "this skill is '
                'three times as important," and scaling every slider up or down changes '
                'nothing. They set <i>fit</i> (Illinois-specific), never translation.</div>',
                unsafe_allow_html=True)
    nv = pd.DataFrame({"skill": [theme.SKILL_LABELS[s] for s in SKILL_ORDER],
                       "weight": [fit.NEED_WEIGHTS[s] * 100 for s in SKILL_ORDER]})
    cc1, cc2 = st.columns([3, 2])
    ch = (alt.Chart(nv).mark_bar(color=theme.ORANGE, height=16).encode(
            x=alt.X("weight:Q", title="default need weight (%)"),
            y=alt.Y("skill:N", sort="-x", title=None),
            tooltip=["skill", alt.Tooltip("weight:Q", format=".0f")])
          .properties(height=210))
    cc1.altair_chart(ch, width='stretch')
    cc2.markdown(
        '<div class="panelbox" style="margin-top:6px"><h4>Why this shape</h4>'
        '<p>Illinois\'s projected frontcourt (the Ivisic brothers, Mirkovic) covers '
        'size and rebounding, so the default tilts toward <b>guard shooting, '
        'creation and efficient experienced scoring</b>. It is an assumption, not '
        'ground truth, which is exactly why it lives on sliders. Move them to '
        'see the board reshuffle.</p></div>', unsafe_allow_html=True)

# ============================================================ OVERVIEW · READING A DOSSIER
with tab_over, st.container(key="ov_dossier"):
    st.markdown(theme.kicker("Reading a dossier",
                "click a player on the Players tab · top to bottom"),
                unsafe_allow_html=True)
    st.markdown("""
<div class="guide">
  <div class="g"><div class="t">Header line<small>origin → destination</small></div>
    <div class="d">Their <b>last school (and season)</b> before the portal, projected
    onto <b>Illinois</b>. The trailing tag reads <b>signed: …</b> where they actually
    committed, or <b>in portal · uncommitted</b></div></div>
  <div class="g"><div class="t">Tags<small>context only</small></div>
    <div class="d"><b>Class</b> (Fr–Gr) · <b>position</b> (Torvik role) ·
    <b>conference</b> (read efficiency stats against this strength of schedule) ·
    <b>ILLINI COMMIT</b> if they picked Illinois · <b>&Delta;L &plusmn;x</b> = the
    competition-level jump (up = stronger program). None of these affect the score.</div></div>
  <div class="g"><div class="t">Three big numbers<small>the pills</small></div>
    <div class="d"><b>Fit percentile</b>: rank within this pool by Illinois's
    need-weighted fit. <b>Translation percentile</b>: team-agnostic "will keep
    producing" rank. <b>Fit score (z)</b>: standard deviations above/below the pool
    average.</div></div>
  <div class="g"><div class="t">Pillar chips<small>Stage-1 screen</small></div>
    <div class="d"><b>Size · Skill · IQ · Character · Fouling</b>, each
    <b>PASS / WARN / FLAG</b>. <i>Hover a chip for the reason.</i> A FLAG demotes the
    player (it never changes the score). <b>Character</b> is a manual call;
    <b>Fouling</b> is data-blocked (greyed N/A).</div></div>
  <div class="g"><div class="t">Stat panel<small>who they are now</small></div>
    <div class="d">The player's <b>actual pre-portal rates</b>, grouped: shooting,
    finishing, creation, rebounding, defense, and per-game.</div></div>
  <div class="g"><div class="t">Projected production<small>left chart</small></div>
    <div class="d">Where each <b>projected</b> rate would land <b>versus this pool</b>
    (percentile). The faint line through each bar is the <b>±MAE uncertainty band</b>;
    long bars (shooting, efficiency) are uncertain.</div></div>
  <div class="g"><div class="t">Skill fit profile<small>right chart</small></div>
    <div class="d">The seven standardised skills as <b>z-scores vs the pool</b>:
    orange is above average, steel below.</div></div>
  <div class="g"><div class="t">Pre → projected<small>bottom table</small></div>
    <div class="d">Each rate <b>before</b> the move vs <b>projected at Illinois</b>, plus
    a <b>likely range</b> (projection ± the model's out-of-sample error).</div></div>
</div>""", unsafe_allow_html=True)
    st.markdown(
        '<div class="note" style="margin-top:14px">Limitations: '
        'survivorship bias (we only learn from transfers who earned minutes); thin '
        'samples for high-major incoming transfers; and entrants with no Division-I '
        '2025-26 season (international/JUCO) cannot be projected.</div>',
        unsafe_allow_html=True)

# ============================================================ WAR ROOM
with tab_war:
    if board is None:
        st.markdown(
            '<div class="panelbox acc"><h4>No 2026-27 portal list loaded</h4>'
            '<p>Drop an entrant list at <code>data/raw/portal_2026.csv</code> '
            '(column <code>player</code>; optional <code>from_team</code>, '
            '<code>pid</code>, <code>committed_to</code>) and reload.</p></div>',
            unsafe_allow_html=True)
    elif view.empty:
        st.info("No players match the current filters.")
    else:
        if str(st.session_state.get("sel_pid")) not in set(view["pid"].astype(str)):
            st.session_state["sel_pid"] = str(view.iloc[0]["pid"])
        sel = str(st.session_state["sel_pid"])

        left, right = st.columns([38, 62], gap="medium")
        with left:
            n_flag_view = int(view["pillar_flag"].sum())
            st.markdown(theme.kicker(
                "Ranked board",
                f"{len(view)} of {len(board)} match filters · "
                f"⚑ {n_flag_view} flagged here · top {min(top_n, len(view))}"),
                unsafe_allow_html=True)
            st.markdown(theme.rail_header(), unsafe_allow_html=True)
            with st.container(height=560):
                for i, (_, r) in enumerate(view.head(top_n).iterrows(), 1):
                    pid = str(r["pid"])
                    gate = "!" if r["pillar_flag"] else " "
                    lab = theme.row_label(i, arrow(r["move"]), gate, r["player"],
                                          r["team"], r["fit_score"],
                                          r["translation_pct"] * 100)
                    st.button(lab, key=f"r_{pid}", on_click=set_sel, args=(pid,),
                              width='stretch',
                              type="primary" if pid == sel else "secondary")
            st.caption(
                f"**Pool** = {len(board)} matched portal entrants. "
                f"**Match filters** = the {len(view)} that clear your sidebar filters "
                "(position / height / class). **⚑ flagged** = trips a Stage-1 pillar "
                f"gate; kept on the board but sorted last. {flagged_n} of the "
                f"{len(board)} pool are flagged; here it's {n_flag_view}.")

        with right:
            r = view[view["pid"].astype(str) == sel].iloc[0]
            skl = {s: r[f"skill_{s}"] for s in SKILL_ORDER}
            top3 = [theme.SKILL_LABELS[k] for k, _ in
                    sorted(skl.items(), key=lambda x: -x[1])[:3]]
            mv = int(r["move"])
            mv_txt = (f" · {'rises' if mv > 0 else 'falls'} {abs(mv)} vs default"
                      if abs(mv) >= 2 else "")
            why = (f"Projects as a <b>{r['archetype'].lower()}</b> who would carry "
                   f"<b>{top3[0].lower()}</b>, <b>{top3[1].lower()}</b> and "
                   f"<b>{top3[2].lower()}</b> to Illinois{mv_txt}.")
            chips = theme.pillar_chips([
                ("Size", r.get("size_status", "na"), str(r.get("size_reason", ""))),
                ("Skill", r.get("skill_status", "na"), str(r.get("skill_reason", ""))),
                ("IQ", r.get("iq_status", "na"), str(r.get("iq_reason", ""))),
                ("Character", "manual", "manual review: the coach's call, never auto-scored"),
                ("Fouling", "blocked",
                 "data-blocked: no fouls-committed field in the Torvik export"),
            ])
            panel = theme.stat_panel([
                ("Shooting", [("3P%", fmt(r.get("three_pct"))), ("FT%", fmt(r.get("ft_pct"))),
                              ("eFG%", fmt(r.get("pre_efg")))]),
                ("Finishing", [("Rim%", fmt(r.get("rim_pct")))]),
                ("Creation", [("AST%", fmt(r.get("pre_ast_pct"))),
                              ("TO%", fmt(r.get("pre_to_pct")))]),
                ("Rebounding", [("ORB%", fmt(r.get("pre_orb_pct"))),
                                ("DRB%", fmt(r.get("pre_drb_pct")))]),
                ("Defense", [("STL%", fmt(r.get("stl_pct"), 1)),
                             ("BLK%", fmt(r.get("blk_pct"), 1))]),
                ("Per game", [("PTS", fmt(r.get("pts_pg"), 1)), ("AST", fmt(r.get("ast_pg"), 1)),
                              ("REB", fmt(r.get("reb_pg"), 1))]),
            ])
            signed_val = str(r.get("signed", "") or "")
            decision = "ILLINI COMMIT" if "illinois" in signed_val.lower() else ""
            type_tag = (str(r["position"]) if pd.notna(r.get("position"))
                        else r["archetype"])
            st.markdown(theme.dossier(
                r["player"], r["team"], info["pre_label"], info["dest_label"],
                r["signed"], r["class_lbl"], type_tag, r["delta_L"],
                r["fit_pct"] * 100, r["translation_pct"] * 100, r["fit_score"], why,
                conf=str(r.get("conf", "") or ""), decision=decision,
                extra_html=chips + panel),
                unsafe_allow_html=True)
            st.write("")

            mae = mae_by_metric()
            d1, d2 = st.columns(2)
            dims = [("Usage", "usage", False), ("Efficiency · TS%", "ts", False),
                    ("Scoring · ORtg", "ortg", False), ("Playmaking · AST%", "ast_pct", False),
                    ("Off. reb", "orb_pct", False), ("Def. reb", "drb_pct", False),
                    ("Ball security", "to_pct", True), ("Availability", "min_pct", False)]
            prod_rows = []
            for l, m, inv in dims:
                pv = float(r[f"proj_{m}"])
                e = mae.get(m, 0.0) or 0.0
                a = pct_of(board[f"proj_{m}"], pv - e, inv)
                b = pct_of(board[f"proj_{m}"], pv + e, inv)
                prod_rows.append({"dim": l, "pct": pct_of(board[f"proj_{m}"], pv, inv),
                                  "lo": min(a, b), "hi": max(a, b)})
            prod = pd.DataFrame(prod_rows)
            base = alt.Chart(prod).encode(y=alt.Y("dim:N", sort=None, title=None))
            bars = base.mark_bar(color=theme.ORANGE, height=13).encode(
                x=alt.X("pct:Q", title="percentile vs pool (bar = projection · line = ±MAE)",
                        scale=alt.Scale(domain=[0, 100])),
                tooltip=[alt.Tooltip("pct:Q", format=".0f", title="pctile"),
                         alt.Tooltip("lo:Q", format=".0f", title="low"),
                         alt.Tooltip("hi:Q", format=".0f", title="high")])
            band = base.mark_rule(color=theme.BONE, strokeWidth=1.5, opacity=0.8).encode(
                x="lo:Q", x2="hi:Q")
            ch1 = (bars + band).properties(height=250,
                                           title="Projected production at Illinois")
            d1.altair_chart(ch1, width='stretch')

            sk = pd.DataFrame([{"skill": theme.SKILL_LABELS[s], "z": float(r[f"skill_{s}"])}
                               for s in SKILL_ORDER])
            ch2 = (alt.Chart(sk).mark_bar(height=15).encode(
                    x=alt.X("z:Q", title="skill (z vs pool)"),
                    y=alt.Y("skill:N", sort="-x", title=None),
                    color=alt.condition(alt.datum.z >= 0, alt.value(theme.ORANGE),
                                        alt.value(theme.STEEL)),
                    tooltip=[alt.Tooltip("z:Q", format="+.2f")])
                  .properties(height=250, title="Skill fit profile"))
            d2.altair_chart(ch2, width='stretch')

            comp_rows = []
            for l, m in [("Usage", "usage"), ("TS%", "ts"), ("ORtg", "ortg"),
                         ("AST%", "ast_pct"), ("TO%", "to_pct"), ("Min%", "min_pct")]:
                pj = float(r[f"proj_{m}"])
                e = mae.get(m)
                comp_rows.append({
                    "Metric": l,
                    "Pre": round(float(r[f"pre_{m}"]), 1),
                    "Projected": round(pj, 1),
                    "± MAE": round(e, 1) if e is not None else None,
                    "Likely range": f"{pj - e:.0f} to {pj + e:.0f}" if e is not None else "n/a",
                })
            comp = pd.DataFrame(comp_rows)
            st.markdown(theme.kicker("Pre-portal → projected at Illinois",
                        "projection ± out-of-sample error"), unsafe_allow_html=True)
            st.dataframe(comp, hide_index=True, width='stretch', column_config={
                "Pre": st.column_config.NumberColumn("Pre", format="%.1f"),
                "Projected": st.column_config.NumberColumn("Projected", format="%.1f"),
                "± MAE": st.column_config.NumberColumn("± MAE", format="%.1f"),
                "Likely range": st.column_config.TextColumn("Likely range"),
            })
            st.markdown('<div class="cap">Likely range = projection ± the model\'s '
                        'out-of-sample mean absolute error for that stat. Efficiency and '
                        'shooting carry the widest bands; the model adds real signal but '
                        'will not pin a single number.</div>', unsafe_allow_html=True)

        st.markdown(theme.kicker("Full board", "Stage-1 pillar status · sortable"),
                    unsafe_allow_html=True)
        ft = view[["player", "team", "pos_lbl", "class_lbl", "size_status",
                   "skill_status", "iq_status", "pillar_flag", "signed", "delta_L",
                   "move", "fit_score", "fit_pct", "translation_pct",
                   "proj_usage", "proj_ts", "proj_ast_pct"]].copy()
        ft["fit_pct"] *= 100
        ft["translation_pct"] *= 100
        st.dataframe(ft, hide_index=True, width='stretch', height=320, column_config={
            "player": "Player", "team": "From", "pos_lbl": "Pos", "class_lbl": "Cls",
            "size_status": "Size", "skill_status": "Skill", "iq_status": "IQ",
            "pillar_flag": st.column_config.CheckboxColumn("Flagged"),
            "signed": "Signed",
            "delta_L": st.column_config.NumberColumn("ΔL", format="%+.1f"),
            "move": st.column_config.NumberColumn("Δrank", format="%+d"),
            "fit_score": st.column_config.NumberColumn("Fit", format="%+.2f"),
            "fit_pct": st.column_config.ProgressColumn("Fit %ile", format="%.0f",
                                                       min_value=0, max_value=100),
            "translation_pct": st.column_config.ProgressColumn("Trans %ile", format="%.0f",
                                                               min_value=0, max_value=100),
            "proj_usage": st.column_config.NumberColumn("USG", format="%.0f"),
            "proj_ts": st.column_config.NumberColumn("TS%", format="%.0f"),
            "proj_ast_pct": st.column_config.NumberColumn("AST%", format="%.0f")})

# ============================================================ OVERVIEW · VALIDATION
with tab_over, st.container(key="ov_valid"):
    st.markdown(theme.kicker("Out-of-sample separation",
                "trained on 2023 · tested on later transfers"), unsafe_allow_html=True)
    st.markdown('<div class="note">Held-out transfers are graded <b>before</b> they '
                'moved, split into four quartiles by that grade, then checked against '
                'what actually happened. Bars run left→right from the '
                '<b>lowest-graded</b> quartile to the <b>highest-graded</b>. A higher '
                'pre-signing translation grade should mean more actual production.</div>',
                unsafe_allow_html=True)
    st.write("")
    sep = separation_table().rename(columns={"bucket": "grade"})
    QLAB = {"Q1": "Q1 · lowest 25%", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4 · highest 25%"}
    qorder = list(QLAB.values())
    sep["grade"] = sep["grade"].astype(str).map(lambda x: QLAB.get(x, x))
    sc = (alt.Chart(sep).mark_bar(color=theme.ORANGE).encode(
            x=alt.X("grade:N", sort=qorder,
                    title="pre-signing translation grade  ·  lowest → highest quartile"),
            y=alt.Y("mean_actual_production:Q", title="actual production after transfer"),
            tooltip=["grade", alt.Tooltip("mean_actual_production:Q", format="+.2f"), "n"])
          .properties(height=300))
    st.altair_chart(sc, width='stretch')
    st.markdown(f'<div class="cap">Spearman(grade, actual) ≈ '
                f'{separation_table().attrs["spearman"]:.2f}: high grades keep '
                f'producing, low grades fade.</div>',
                unsafe_allow_html=True)

    st.markdown(theme.kicker("Would it have flagged Underwood's signings?"),
                unsafe_allow_html=True)
    st.dataframe(signings_table(), hide_index=True, width='stretch')
    st.markdown('<div class="cap">All four grade in the upper tier on '
                'translation from their pre-transfer season. Need weights are not '
                'tuned to these players.</div>', unsafe_allow_html=True)

    st.markdown(theme.kicker("Stage-1 pillar screen vs known outcomes"),
                unsafe_allow_html=True)
    st.markdown('<div class="note">A useful screen clears the genuine hits and flags the '
                'genuine risks. Left: the four signings, graded purely from their '
                '<b>pre-transfer</b> season. Right: entrants the screen flags on a '
                'specific pillar.</div>',
                unsafe_allow_html=True)
    st.write("")
    pv1, pv2 = st.columns(2)
    with pv1:
        st.dataframe(pillar_hits(), hide_index=True, width='stretch')
        st.markdown('<div class="cap">All four clear the active gates, including '
                    '<b>Marcus Domask</b> (6-6, ~95th-percentile height for a guard, no '
                    'skill deficiency), so the screen would not have removed '
                    'Underwood\'s actual hits.</div>', unsafe_allow_html=True)
    with pv2:
        st.dataframe(pillar_flagged(), hide_index=True, width='stretch')
        st.markdown('<div class="cap">Illustrative: flagged on shooting / size / IQ '
                    'from their own pre-portal profile, before any ranking.</div>',
                    unsafe_allow_html=True)

# ============================================================ OVERVIEW · ROADMAP
with tab_over, st.container(key="ov_road"):
    st.markdown(theme.kicker("Where this goes next", "natural extensions, in priority order"),
                unsafe_allow_html=True)
    st.markdown('<div class="note">Planned extensions of the engine, in rough priority '
                'order. The first two close the documented data gaps in the pillar '
                'screen.</div>',
                unsafe_allow_html=True)
    st.write("")
    FUTURE_USES = [
        ("Turn the fouling pillar on", "once a Torvik re-pull includes fouls-committed and "
         "opponent FT-rate, activate the blocked fifth pillar."),
        ("Add weight and wingspan", "upgrade the size pillar from height-only to true frame "
         "once the data exists."),
        ("NIL and budget fit", "layer projected production against cost to find value buys."),
        ("Scenario planning", "re-weight the need vector to a hypothetical roster gap "
         "(\"who fits if player X leaves?\")."),
        ("Portal entry alerts", "flag when a player matching the need vector enters the "
         "portal."),
        ("Recruiting board", "ingest high-school, JUCO, and European sources for a true multi-source "
         "board."),
    ]
    items = "".join(
        f'<p><b>{theme._esc(t)}</b>: {theme._esc(d)}</p>' for t, d in FUTURE_USES)
    st.markdown(f'<div class="panelbox acc">{items}</div>', unsafe_allow_html=True)

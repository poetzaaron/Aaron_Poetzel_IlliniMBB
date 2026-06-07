# Illinois Portal-Evaluation Engine: Translation Model (Phase A)

A reusable transfer-portal evaluation engine for Illinois men's basketball,
**validated retrospectively**. The core IP is a *translation model*: given a
player's pre-transfer season and the size of the competition-level jump, it
projects how their production will translate at the new school.

> A **reusable** engine: validated on history (the backtest would have flagged
> Underwood's real hits: Terrence Shannon Jr., Kylan Boswell, Andrej Stojakovic),
> then pointed forward to rank the **2026-27 portal** for Illinois fit.

This repo contains **Phase A** (transfer-pair dataset, translation model,
out-of-sample validation), **Phase B** (transparent fit layer + retrospective
backtest on Illinois's own portal history), and **Phase C**, **IlliniPortal**,
a dark scouting terminal that ranks the **live 2026-27 portal** for Illinois with
coach-adjustable need weights, alongside the validated backtest cycles.

## Results (out-of-sample)

Trained on transfers landing in 2023; tested on 2024–2026. The model beats a
naive "production stays the same" baseline on **all 9 metrics**:

| metric  | MAE (model) | MAE (naive) | R² (model) | R² (naive) | MAE gain |
|---------|------------:|------------:|-----------:|-----------:|---------:|
| usage   | 3.58 | 4.58 |  0.18 | −0.37 | 22% |
| ortg    | 11.89 | 15.24 | 0.06 | −0.72 | 22% |
| efg     | 7.22 | 9.81 |  0.08 | −0.79 | 26% |
| ts      | 6.70 | 9.20 |  0.06 | −0.86 | 27% |
| orb%    | 2.13 | 2.25 |  0.41 |  0.14 |  6% |
| drb%    | 3.27 | 3.83 |  0.27 | −0.19 | 15% |
| ast%    | 4.35 | 4.89 |  0.37 |  0.16 | 11% |
| to%     | 4.81 | 6.14 |  0.07 | −0.71 | 22% |
| min%    | 18.87 | 24.32 | 0.16 | −0.58 | 22% |

The naive baseline's negative R² is the point: raw pre-transfer numbers don't
carry over; the model captures **level-adjusted regression to the mean**.
Reproduce with `python scripts/evaluate.py`.

## Phase B: fit layer + Illinois backtest

The fit layer is deliberately transparent (`fit.py`): projected metrics → seven
standardised **skills** (shooting, shot-creation, playmaking, ball-security,
rebounding, efficiency, availability) → two scores:

- **translation score**: will this profile keep *producing* at the new level?
  (team-agnostic skill blend)
- **fit score**: translation re-weighted by Illinois's **need vector** plus an
  explicit **experience bonus** (Underwood's stated recipe). The need vector is a
  documented, editable assumption; frontcourt returners cover size, so it tilts
  to guard shooting/creation/efficiency.

Every score ships with its skill breakdown, so a player card reads
"fits because shooting + creation + experience," never a black-box number.

**Backtest** (`scripts/backtest.py`), validated on Underwood's real signings:

1. *Out-of-sample separation*: train on 2023, grade held-out 2024–26 transfers
   from their pre-transfer season, bucket by grade. Mean **actual** post-transfer
   production rises monotonically across quartiles (−0.32 → +0.27; Spearman
   ≈ 0.40). High grades keep producing; low grades fade, the two-sided
   keepers-vs-busts result, with no cherry-picking.
2. *The signings translated*: Shannon, Domask, Boswell, Stojakovic all grade in
   the upper tier on translation from their pre-transfer seasons; the model would
   have endorsed each as a player who'd keep producing after the jump. Projected
   profiles closely track what actually happened.
3. *Face validity*: the 2026-portal-to-Illinois demo board surfaces genuinely
   coveted portal names at the top (`data/processed/illinois_board_2026.csv`).

> Note: the need-vector weights are **not** tuned to make the three
> signings top the *fit* board (that would be fitting to three points). Their fit
> percentile is middling; the *translation* grade is the validated headline.

## Phase C: the IlliniPortal terminal

A dark scouting terminal (`app/streamlit_app.py` + `app/theme.py`), branded
**IlliniPortal**: ink `#0E1116` / Illini-orange `#FF5F05`, Space Grotesk + IBM Plex
Mono/Sans, an asymmetric status-bar + 38/62 master-detail layout (deliberately not the
default Streamlit look). It runs the Phase A/B pipeline live (cached), so the sliders
re-rank in real time. Two tabs:

- **Overview**: everything but the board, in one place: Illinois's 2026-27 **roster
  context** (returning core, departures and the gap each leaves, incoming commits),
  with an up-front note that the screen runs four of five pillars (fouling is
  data-blocked); the plain-language **explainer** (translation model, its out-of-sample
  **accuracy** table, how the level jump **ΔL** is calculated, the need vector and its
  0–100 weight scale, how to read a dossier); the full **validation** (out-of-sample
  separation, signing flags, the pillar screen clearing hits and flagging risks); and a
  **roadmap** for future uses.
- **Players**: the board. Pick a **cycle**: the **live 2026-27 portal** (forward) or a
  completed **backtest** cycle. The **Stage-1 pillar screen** flags/demotes
  gate-failures (a `!` marker in the rail + a clear/flagged count; toggle to
  hard-filter). A dense **clickable ranked rail** (click any row) drives a full player
  **dossier**: pillar status chips, a grouped stat panel,
  Committed/Targeted tags, and projected production shown with **uncertainty bands**
  (each projection ± its out-of-sample MAE, both as ranged percentile bars and a
  "likely range" column, so shooting/efficiency read as wide and honest rather than
  falsely precise). The need-weight sliders re-rank live, with a **Δrk** column showing
  movement vs the default weights.

### Forward 2026-27 portal (data contract)

The upcoming portal can't be detected from completed seasons, so the entrant list
is an input. Commit **`data/raw/portal_2026.csv`** (template: `portal_2026.template.csv`):
column `player` required; `from_team` / `pid` / `committed_to` optional. The app
matches entrants to their 2025-26 (`year==2026`) stats by pid → name+team → name
(homonyms resolve to the higher-minutes player; `Mike`↔`Michael` recovered),
projects them onto Illinois (2025-26 strength as the 2026-27 proxy), and ranks by
fit. Entrants with no 2025-26 D1 season (international/JUCO) can't be projected and
are reported as unmatched.

```bash
streamlit run app/streamlit_app.py
```

Deploys free on **Streamlit Community Cloud**: point it at `app/streamlit_app.py`
with the root `requirements.txt`. Self-contained; the committed `data/raw/` CSVs
(seasons + portal list) are processed at startup, no prebuilt artifacts needed.

## Stage 1: the four-pillar screen

A screening layer runs **in front of** the engine, operationalizing the framework
Illinois's GM described publicly. It is a two-stage flow: **Stage 1 (`pillars.py`)
decides eligibility; Stage 2 (the translation + fit engine) decides rank.** The
pillars are **floors and flags, not a weighted average**; one strength can't offset
a disqualifying weakness, and shooting is weighted hardest (the canonical
disqualifier). Stats are read from a player's pre-transfer season, and percentile
floors are taken **within position group** (a guard is measured against guards).

| Pillar | How it's screened | Status |
|--------|-------------------|--------|
| **Positional size** | height percentile within position (no weight/wingspan in the data → manual note) | active |
| **No skill deficiency** | shooting (3P%/FT%/TS%, hardest), rim finishing, rebounding, passing, defensive activity (weak proxy) | active |
| **Basketball IQ** | AST:TO ratio, ranked within position; labeled a proxy | active |
| **Character** | manual flag + notes, never auto-scored | manual |
| **Defensive fouling discipline** | n/a | **data-blocked** |

**Fouling discipline is part of the framework but data-blocked**, not omitted: the
Torvik export carries no fouls-committed or opponent-free-throw-rate field, so it is
reported as `blocked` and is the first addition pending a data re-pull. Size is
**height-only** for the same reason (weight/wingspan are documented next steps).

Two principles are load-bearing. **Roster context drives defaults, not scores**: the
current backcourt void only sets where the board opens (guard/wing, 6-3+; need vector
tilted to shooting/creation/efficiency, with experience up-weighted in the fit score),
never how a player is graded.
And **flagged players are demoted, not deleted** by default: their fit score is
untouched and they stay visible, because the model's value is its freedom to *disagree*
with the staff. The Overview's validation section shows the screen clearing Underwood's hits (Shannon,
Domask, Boswell, Stojakovic all clear the active gates from their pre-transfer seasons)
and flagging non-shooting or undersized busts.

## The model

For each metric, an interpretable ridge regression:

```
Stat_post = b0 + b1·Stat_pre + b2·ΔL + b3·(Stat_pre × ΔL) + g'·Z + e
```

- **ΔL** (`delta_L`) is the level jump: destination adjEM − origin adjEM
  (adjEM = adjOE − adjDE from Torvik team ratings). `delta_sos` / `delta_barthag`
  are available alternates.
- **interaction** `Stat_pre × ΔL`: lets a bigger jump penalize different
  players differently (high-usage mid-major scorers shed the most moving up).
- **Z controls**: `usage_pre`, `min_pct_pre`, `gp_pre`, and `age_proxy_pre`
  (experience, up-weighted later per Underwood's stated philosophy).

One `RidgeCV` per metric (`StandardScaler` + CV-selected α), so coefficients stay
legible; see `data/processed/coefficients.csv` after training.

## Data

Torvik exports committed to `data/raw/` (live scraping is blocked in this
environment; the pipeline runs offline against local files):

- `player_<YYYY>.csv`: Torvik advanced player stats. **Headerless/positional**;
  the loader decodes columns by index (see `config.POSITIONAL_PLAYER`).
- `<YYYY>_team_results.csv`: Torvik team ratings (`adjoe`, `adjde`, `barthag`,
  `sos`). Header-based; column names are mapped via aliases.

Seasons **2022–2026** (Torvik labels a season by its ending year). Transfers are
**detected from the data itself**: a player at team A in season *t* and a
different D1 team B in *t+1*. Identity uses the stable Torvik `pid` (all 4,291
detected pairs matched on `pid`, zero ambiguous).

## Layout

```
data/raw/                 # Torvik CSVs (committed)
data/processed/           # generated: transfer_pairs.parquet, model, coefficients
src/illiniportal/
  config.py               # paths, schema, aliases, positional map, constants
  data_load.py            # load + normalise player (positional) & team files
  transfers.py            # detect transfer pairs + attach team-strength ΔL
  features.py             # per-metric design matrices (pre, ΔL, interaction, Z)
  model.py                # TranslationModel: ridge-per-metric, save/load
  validate.py             # temporal split, MAE/RMSE/R² vs naive baseline
  project.py              # project a player's pre season onto a destination
  fit.py                  # skills, translation score, Illinois need-vector fit
  pillars.py              # Stage-1 four-pillar screen (size/skill/IQ/character)
  backtest.py             # signing flags, projected-vs-actual, OOS separation
  portal.py               # forward-mode: ingest + match a 2026-27 portal list
scripts/build_dataset.py  # raw CSVs -> transfer_pairs.parquet (+ sanity report)
scripts/train.py          # fit model, write artifact + coefficient table
scripts/evaluate.py       # out-of-sample validation table
scripts/backtest.py       # Phase B backtest + Illinois target board
scripts/make_synthetic_data.py  # Torvik-shaped fixture for offline smoke tests
app/streamlit_app.py      # Phase C interactive scouting app
app/theme.py              # custom Illini theme (CSS + Altair) and HTML builders
```

## Run it

```bash
pip install -r requirements.txt
python scripts/build_dataset.py   # detect transfers, sanity report
python scripts/train.py           # fit + save model and coefficients
python scripts/evaluate.py        # out-of-sample validation table
python scripts/backtest.py        # Illinois backtest + target board
streamlit run app/streamlit_app.py  # the IlliniPortal terminal (Phase C)
pytest                            # 36 tests (logic, pillar screen, portal, app smoke)
```

Tests run against hand-built fixtures (transfer-detection edge cases, feature
dedup, name-identity fallback) and a synthetic Torvik-shaped dataset for a full
offline end-to-end check; no real data or network needed. The per-signing
projected-vs-actual figures use **leave-one-out** (the model is re-fit without
that player), so they are genuinely out-of-sample.

No live-data fetch from this container (network is allowlisted to GitHub/PyPI);
refresh by committing updated Torvik CSVs to `data/raw/`.

## Limitations

- **Survivorship bias**: we only observe transfers who got minutes at the new
  school; the model is conditional on playing.
- **Small samples** for high-major *incoming* transfers specifically.
- **Name-matching** would be a risk without `pid`; here `pid` is present, so it's
  not a factor for this dataset.

## Roadmap

Phases A–C plus the Stage-1 pillar screen are in place. Natural extensions, in
priority order: **defensive fouling discipline** (the blocked fifth pillar, which needs a
Torvik re-pull that includes fouls-committed / opponent free-throw rate), **weight and
wingspan** for the size pillar (height-only today); then a multi-output
gradient-boosted translation model (XGBoost) as an accuracy upgrade over per-metric
ridge, and wiring the need vector to explicit roster-gap inputs.

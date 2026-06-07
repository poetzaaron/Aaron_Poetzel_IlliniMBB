"""IlliniPortal theme: dark scouting terminal (Bloomberg-meets-ESPN), Illini accent.

Color: ink #0E1116 / panel #161A21 / hairline #232A34 / bone #ECECE4, accent
Illini Orange #FF5F05, data hi/lo amber #FFB000 / steel #5B7A99 (not green/red).
Type: Space Grotesk (display) + IBM Plex Mono (all numbers) + IBM Plex Sans (body).
Plex Mono gives true tabular alignment for a terminal; Space Grotesk reads
mechanical without being generic. Layout: status bar + asymmetric 38/62
master-detail, density over decoration.
"""

from __future__ import annotations

import html

import altair as alt

INK = "#0E1116"
PANEL = "#161A21"
PANEL2 = "#1C2230"
LINE = "#232A34"
BONE = "#ECECE4"
MUTE = "#8A93A0"
ORANGE = "#FF5F05"
AMBER = "#FFB000"
STEEL = "#5B7A99"

SKILL_LABELS = {
    "shooting": "Shooting", "shot_creation": "Shot creation",
    "playmaking": "Playmaking", "ball_security": "Ball security",
    "rebounding": "Rebounding", "efficiency": "Efficiency",
    "availability": "Availability",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root{
  --ink:#0E1116; --panel:#161A21; --panel2:#1C2230; --line:#232A34;
  --bone:#ECECE4; --mute:#8A93A0; --orange:#FF5F05; --amber:#FFB000; --steel:#5B7A99;
}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"]{display:none!important;}
header[data-testid="stHeader"]{background:transparent;height:0;}
html, body, [class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:var(--ink);color:var(--bone);}
.block-container{padding-top:.6rem;padding-bottom:2rem;max-width:1500px;}
.mono{font-family:'IBM Plex Mono',monospace;}
h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif;color:var(--bone);letter-spacing:.3px;}
::-webkit-scrollbar{width:9px;height:9px;}
::-webkit-scrollbar-track{background:var(--ink);}
::-webkit-scrollbar-thumb{background:#2A3340;border-radius:0;}
::-webkit-scrollbar-thumb:hover{background:#37424f;}
a{color:var(--orange);}

/* ---- status bar ---- */
.status{display:flex;align-items:stretch;gap:0;background:var(--panel);
  border:1px solid var(--line);border-left:3px solid var(--orange);margin-bottom:14px;}
.status .brand{font-family:'Space Grotesk';font-weight:700;font-size:15px;
  letter-spacing:1px;color:#fff;padding:12px 16px;border-right:1px solid var(--line);
  display:flex;align-items:center;white-space:nowrap;}
.status .brand em{color:var(--orange);font-style:normal;}
.status .cell{padding:9px 16px;border-right:1px solid var(--line);}
.status .cell .l{font-family:'IBM Plex Mono';font-size:9.5px;letter-spacing:1.5px;
  text-transform:uppercase;color:var(--mute);}
.status .cell .v{font-family:'IBM Plex Mono';font-size:14px;color:var(--bone);margin-top:3px;}
.status .cell .v.hot{color:var(--orange);}
.status .spacer{flex:1;}
.status .live{padding:9px 16px;font-family:'IBM Plex Mono';font-size:10px;letter-spacing:1.5px;
  color:var(--ink);background:var(--orange);align-self:stretch;display:flex;align-items:center;font-weight:600;}

/* ---- section kicker ---- */
.kick{display:flex;align-items:center;gap:10px;margin:18px 2px 10px;}
.kick .b{width:8px;height:8px;background:var(--orange);}
.kick .t{font-family:'Space Grotesk';font-weight:600;font-size:13px;letter-spacing:2px;
  text-transform:uppercase;color:var(--bone);}
.kick .n{font-family:'IBM Plex Mono';font-size:11px;color:var(--mute);margin-left:auto;}

/* ---- master rail ---- */
.railhead{font-family:'IBM Plex Mono';font-size:10px;letter-spacing:.5px;color:var(--mute);
  text-transform:uppercase;padding:6px 12px;border-bottom:1px solid var(--line);
  white-space:pre;background:var(--panel);}
/* buttons-as-rows: the ONLY buttons on the board are master rows */
.stButton>button{width:100%;text-align:left;justify-content:flex-start;
  font-family:'IBM Plex Mono',monospace;font-size:12.5px;line-height:1.2;
  background:var(--panel);color:#C9D1D9;border:none;border-bottom:1px solid var(--line);
  border-radius:0;padding:8px 12px;white-space:pre;letter-spacing:0;min-height:0;}
.stButton>button:hover{background:var(--panel2);color:#fff;}
.stButton>button:focus{box-shadow:none!important;}
.stButton>button[kind="primary"]{background:var(--panel2);color:#fff;
  box-shadow:inset 3px 0 0 var(--orange)!important;}

/* ---- dossier ---- */
.dossier{background:var(--panel);border:1px solid var(--line);}
.dh{padding:18px 22px;border-bottom:1px solid var(--line);position:relative;}
.dh:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--orange);}
.dh .nm{font-family:'Space Grotesk';font-weight:700;font-size:30px;line-height:1;color:#fff;}
.dh .pth{font-family:'IBM Plex Mono';font-size:12.5px;color:var(--mute);margin-top:9px;}
.dh .pth b{color:var(--bone);}
.dh .pth .sg{color:var(--orange);}
.dh .tags{margin-top:11px;display:flex;gap:8px;flex-wrap:wrap;}
.tag{font-family:'IBM Plex Mono';font-size:10.5px;letter-spacing:.5px;color:var(--bone);
  border:1px solid var(--line);padding:3px 9px;background:var(--ink);}
.tag.o{color:var(--orange);border-color:#3a2410;}
.pills{display:flex;border-bottom:1px solid var(--line);}
.pill{flex:1;padding:14px 18px;border-right:1px solid var(--line);}
.pill:last-child{border-right:none;}
.pill .v{font-family:'Space Grotesk';font-weight:700;font-size:26px;color:var(--bone);line-height:1;}
.pill .v.hot{color:var(--orange);}
.pill .l{font-family:'IBM Plex Mono';font-size:9.5px;letter-spacing:1.4px;text-transform:uppercase;
  color:var(--mute);margin-top:6px;}
.why{padding:13px 22px;font-size:13px;color:#C9D1D9;border-bottom:1px solid var(--line);line-height:1.5;}
.why b{color:var(--orange);font-weight:600;}

/* ---- pillar status strip + grouped stat panel ---- */
.pstrip{display:flex;flex-wrap:wrap;gap:7px;padding:12px 22px;border-bottom:1px solid var(--line);}
.chip{font-family:'IBM Plex Mono';font-size:10px;letter-spacing:.4px;padding:4px 9px;
  border:1px solid var(--line);display:flex;gap:7px;align-items:center;background:var(--ink);}
.chip .k{color:var(--mute);text-transform:uppercase;}
.chip .s{font-weight:600;}
.chip.pass{border-color:#23323f;} .chip.pass .s{color:var(--steel);}
.chip.warn{border-color:#3a3410;} .chip.warn .s{color:var(--amber);}
.chip.flag{border-color:#3a2410;} .chip.flag .s{color:var(--orange);}
.chip.blocked{opacity:.55;} .chip.blocked .s{color:var(--mute);}
.chip.manual .s{color:var(--mute);} .chip.na .s{color:var(--mute);}
.spanel{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);
  border-bottom:1px solid var(--line);}
.sgrp{background:var(--panel);padding:11px 14px;}
.sgrp .h{font-family:'IBM Plex Mono';font-size:9px;letter-spacing:1.2px;text-transform:uppercase;
  color:var(--mute);margin-bottom:7px;}
.sgrp .r{display:flex;justify-content:space-between;font-family:'IBM Plex Mono';font-size:12px;padding:2px 0;}
.sgrp .r .lab{color:#9aa3ad;} .sgrp .r .val{color:var(--bone);}

/* ---- overview / explainer ---- */
.lede{font-size:16px;line-height:1.6;color:#C9D1D9;max-width:760px;}
.lede b{color:#fff;}
.panelbox{background:var(--panel);border:1px solid var(--line);padding:18px 20px;height:100%;}
.panelbox.acc{border-left:3px solid var(--orange);}
.panelbox h4{font-size:13px;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 10px;color:#fff;}
.panelbox p{font-size:13px;line-height:1.6;color:#B9C2CC;margin:0 0 8px;}
.panelbox .eq{font-family:'IBM Plex Mono';font-size:12.5px;color:var(--amber);
  background:var(--ink);border:1px solid var(--line);padding:10px 12px;margin:8px 0;overflow-x:auto;}
.panelbox code{font-family:'IBM Plex Mono';color:var(--orange);background:var(--ink);padding:1px 5px;}
.steps{list-style:none;padding:0;margin:6px 0 0;}
.steps li{font-size:12.5px;color:#B9C2CC;padding:5px 0 5px 26px;position:relative;border-top:1px solid var(--line);}
.steps li:before{content:attr(data-n);position:absolute;left:0;top:5px;font-family:'IBM Plex Mono';
  font-size:11px;color:var(--orange);border:1px solid #3a2410;width:17px;height:17px;
  display:flex;align-items:center;justify-content:center;}
.legend{font-family:'IBM Plex Mono';font-size:11.5px;color:var(--mute);line-height:1.9;}
.legend b{color:var(--bone);}

/* ---- sidebar ---- */
[data-testid="stSidebar"]{background:var(--panel);border-right:1px solid var(--line);}
[data-testid="stSidebar"] *{color:#C9D1D9;}
[data-testid="stSidebar"] label{color:var(--bone)!important;font-size:12px!important;}
.sbh{font-family:'Space Grotesk';font-weight:700;font-size:16px;color:#fff;letter-spacing:1px;}
.sbh em{color:var(--orange);font-style:normal;}
.sbk{font-family:'IBM Plex Mono';text-transform:uppercase;letter-spacing:2px;font-size:9.5px;
  color:var(--mute);margin:14px 0 4px;border-top:1px solid var(--line);padding-top:12px;}
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"]{padding-top:2px;}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"]{gap:0;border-bottom:1px solid var(--line);background:transparent;}
.stTabs [data-baseweb="tab"]{font-family:'Space Grotesk';font-weight:600;letter-spacing:1.5px;
  text-transform:uppercase;font-size:12.5px;color:var(--mute);padding:10px 18px;background:transparent;}
.stTabs [aria-selected="true"]{color:#fff;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--orange);height:2px;}

[data-testid="stDataFrame"]{border:1px solid var(--line);}
.note{color:var(--mute);font-size:12px;line-height:1.6;}
.cap{font-family:'IBM Plex Mono';font-size:11px;color:var(--mute);}
hr{border-color:var(--line);}

/* ---- Overview: ~1.5x readability bump, scoped to the Overview tab only
   (st.container(key="ov_*") emits a .st-key-ov_* wrapper). The dense Players
   board uses different classes and is left at its compact size. ---- */
[class*="st-key-ov_"] .lede{font-size:19px;line-height:1.6;max-width:900px;}
[class*="st-key-ov_"] .kick .t{font-size:15px;}
[class*="st-key-ov_"] .kick .n{font-size:12.5px;}
[class*="st-key-ov_"] .panelbox h4{font-size:15px;}
[class*="st-key-ov_"] .panelbox p{font-size:15.5px;line-height:1.6;}
[class*="st-key-ov_"] .panelbox .eq{font-size:15px;}
[class*="st-key-ov_"] .panelbox code{font-size:14px;}
[class*="st-key-ov_"] .panelbox .cap{font-size:13px;}
[class*="st-key-ov_"] .steps li{font-size:15px;padding-left:28px;}
[class*="st-key-ov_"] .legend{font-size:14px;line-height:1.9;}
[class*="st-key-ov_"] .note{font-size:15px;line-height:1.6;}
[class*="st-key-ov_"] .cap{font-size:14px;}

/* ---- "Reading a dossier" guide ---- */
.guide{border:1px solid var(--line);background:var(--panel);}
.guide .g{display:grid;grid-template-columns:215px 1fr;gap:20px;padding:14px 20px;
  border-bottom:1px solid var(--line);}
.guide .g:last-child{border-bottom:none;}
.guide .t{font-family:'IBM Plex Mono';color:var(--orange);font-size:15px;font-weight:500;}
.guide .t small{display:block;color:var(--mute);font-size:12px;margin-top:3px;letter-spacing:.3px;}
.guide .d{color:#C9D1D9;font-size:16px;line-height:1.6;}
.guide .d b{color:var(--bone);}
</style>
"""


def _esc(s):
    return html.escape(str(s))


def status_bar(cells, live_label="") -> str:
    out = ['<div class="status">',
           '<div class="brand">Illini<em>Portal</em></div>']
    for l, v, hot in cells:
        cls = " hot" if hot else ""
        out.append(f'<div class="cell"><div class="l">{_esc(l)}</div>'
                   f'<div class="v{cls}">{_esc(v)}</div></div>')
    out.append('<div class="spacer"></div>')
    if live_label:
        out.append(f'<div class="live">{_esc(live_label)}</div>')
    out.append('</div>')
    return "".join(out)


def kicker(title, note="") -> str:
    n = f'<div class="n">{_esc(note)}</div>' if note else ""
    return f'<div class="kick"><div class="b"></div><div class="t">{_esc(title)}</div>{n}</div>'


def dossier(name, origin, pre_year, dest_label, signed, klass, archetype,
            delta_L, fit_pct, trans_pct, fit_score, why_html,
            conf="", decision="", extra_html="") -> str:
    direction = "up" if delta_L > 0 else "down"
    signed_html = (f'<span class="sg">signed: {_esc(signed)}</span>' if signed
                   else '<span style="color:#6b7480">in portal · uncommitted</span>')
    tags = [f'<span class="tag">{_esc(klass)}</span>',
            f'<span class="tag o">{_esc(archetype)}</span>']
    if conf:
        tags.append(f'<span class="tag">{_esc(conf)}</span>')
    if decision:
        tags.append(f'<span class="tag o">{_esc(decision)}</span>')
    tags.append(f'<span class="tag">&Delta;L {delta_L:+.1f} &middot; step {direction}</span>')
    # NOTE: emit as ONE line with no blank lines; Streamlit's markdown ends an HTML
    # block at the first blank line, which would dump the rest as literal text.
    return (
        '<div class="dossier">'
        f'<div class="dh"><div class="nm">{_esc(name)}</div>'
        f'<div class="pth">{_esc(origin)} ({pre_year}) &nbsp;&rarr;&nbsp; '
        f'<b>ILLINOIS</b> ({_esc(dest_label)}) &nbsp;·&nbsp; {signed_html}</div>'
        f'<div class="tags">{"".join(tags)}</div></div>'
        '<div class="pills">'
        f'<div class="pill"><div class="v hot">{fit_pct:.0f}</div>'
        '<div class="l">Fit percentile</div></div>'
        f'<div class="pill"><div class="v">{trans_pct:.0f}</div>'
        '<div class="l">Translation %ile</div></div>'
        f'<div class="pill"><div class="v">{fit_score:+.2f}</div>'
        '<div class="l">Fit score (z)</div></div></div>'
        f'<div class="why">{why_html}</div>{extra_html}</div>'
    )


_STATUS_GLYPH = {"pass": "PASS", "warn": "WARN", "flag": "FLAG",
                 "blocked": "N/A", "manual": "MANUAL", "na": "n/a"}


def pillar_chips(items) -> str:
    """items: list of (label, status, reason). Status drives color; reason = hover."""
    out = ['<div class="pstrip">']
    for label, status, reason in items:
        cls = status if status in _STATUS_GLYPH else "na"
        glyph = _STATUS_GLYPH.get(status, "n/a")
        out.append(f'<div class="chip {cls}" title="{_esc(reason)}">'
                   f'<span class="k">{_esc(label)}</span>'
                   f'<span class="s">{glyph}</span></div>')
    out.append('</div>')
    return "".join(out)


def stat_panel(groups) -> str:
    """groups: list of (title, [(label, value_str), ...]) -> grouped mono panel."""
    out = ['<div class="spanel">']
    for title, rows in groups:
        cells = "".join(f'<div class="r"><span class="lab">{_esc(l)}</span>'
                        f'<span class="val">{_esc(v)}</span></div>' for l, v in rows)
        out.append(f'<div class="sgrp"><div class="h">{_esc(title)}</div>{cells}</div>')
    out.append('</div>')
    return "".join(out)


def rail_header() -> str:
    return ('<div class="railhead">'
            + f'{"#":>2} {"":1}{"!":1} {"PLAYER":<19} {"FROM":<12}{"FIT":>6}{"TR":>4}'
            + '</div>')


def row_label(rank, arrow, gate, name, origin, fit, trans) -> str:
    """``gate`` = "!" when the player trips a Stage-1 pillar (flagged/demoted)."""
    name = (str(name)[:18])
    origin = (str(origin)[:11])
    return f"{rank:>2} {arrow:1}{gate:1} {name:<19}{origin:<12}{fit:>6.2f}{trans:>4.0f}"


def register_altair_theme():
    def _t():
        return {"config": {
            "background": "transparent", "font": "IBM Plex Sans",
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": MUTE, "titleColor": MUTE,
                     "labelFont": "IBM Plex Mono", "titleFont": "IBM Plex Mono",
                     "titleFontSize": 10, "labelFontSize": 10,
                     "grid": False, "domainColor": LINE, "tickColor": LINE},
            "axisY": {"grid": True, "gridColor": "#1B2027", "gridWidth": 1},
            "axisX": {"grid": False},
            "legend": {"labelColor": MUTE, "titleColor": MUTE,
                       "labelFont": "IBM Plex Mono", "titleFont": "IBM Plex Mono"},
            "title": {"color": BONE, "font": "Space Grotesk", "fontSize": 13,
                      "anchor": "start", "subtitleColor": MUTE},
            "range": {"category": [ORANGE, STEEL, AMBER, "#7E93B2", "#C9D1D9"]},
        }}
    try:
        alt.theme.register("warroom", enable=True)(_t)
    except Exception:
        try:
            alt.themes.register("warroom", _t); alt.themes.enable("warroom")
        except Exception:
            pass

"""
ui.py — shared look & feel for every dashboard page
(colors, CSS, KPI cards, chart styling, cached data loading).
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics as m  # noqa: E402

# ----------------------------------------------------------------------------
# Color system (validated categorical palette + reserved status colors)
# ----------------------------------------------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = SERIES
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
INK, INK_2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
NEUTRAL_BAR = "#9ec5f4"

PLANT_COLORS = {"Dearborn Truck Assembly": BLUE, "Lansing SUV Assembly": ORANGE, "Toledo Drivetrain Plant": AQUA}
REGION_COLORS = {"Domestic": BLUE, "Nearshore": AQUA, "Overseas": ORANGE}
RESULT_COLORS = {"Pass": GOOD, "Conditional": WARNING, "Fail": CRITICAL}
CAUSE_COLORS = {"Part Shortage": RED, "Machine Breakdown": BLUE, "Changeover": AQUA,
                "Quality Hold": YELLOW, "Labor": VIOLET}
STATUS_COLORS = {"Preferred": GOOD, "Approved - monitor": WARNING, "Corrective action required": CRITICAL}

CSS = """
<style>
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --card:#ffffff; --line:rgba(11,11,11,.08); }
.block-container { padding-top: 3.6rem; padding-bottom: 3rem; max-width: 1400px; }
html, body, [class*="css"] { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }

/* hero banner */
.hero { background: linear-gradient(120deg, #0d366b 0%, #1c5cab 45%, #2a78d6 75%, #1baf7a 120%);
        color: #fff; border-radius: 18px; padding: 22px 26px; margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(13,54,107,.18); }
.hero h1 { color:#fff; font-size: 1.65rem; margin: 0 0 4px 0; line-height: 1.25; font-weight: 750; }
.hero p  { color: rgba(255,255,255,.88); margin: 0; font-size: .95rem; }
.hero .tag { display:inline-block; background: rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28);
             padding: 2px 10px; border-radius: 999px; font-size: .75rem; margin: 0 6px 8px 0; }

/* KPI cards: responsive grid, wraps on phones */
.kpi-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 4px 0 18px; }
.kpi { background: var(--card); border:1px solid var(--line); border-radius: 14px; padding: 14px 16px 12px;
       position: relative; overflow: hidden; box-shadow: 0 2px 8px rgba(11,11,11,.04); }
.kpi::before { content:""; position:absolute; left:0; top:0; bottom:0; width:5px; background: var(--accent); }
.kpi .label { color: var(--ink2); font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.kpi .value { color: var(--ink); font-size: 1.7rem; font-weight: 750; margin: 2px 0 2px; line-height: 1.2; }
.kpi .value.txt { font-size: 1.12rem; line-height: 1.3; margin: 6px 0 4px; }
.kpi .note  { color: var(--muted); font-size: .78rem; }
.kpi .pill  { display:inline-block; font-size:.72rem; font-weight:700; padding:1px 8px; border-radius:999px;
              margin-right: 4px; color:#fff; }
.pill.good { background:#0ca30c; } .pill.warn { background:#fab219; color:#0b0b0b; } .pill.bad { background:#d03b3b; }

/* section titles & insight boxes */
.sec { font-size: 1.08rem; font-weight: 700; color: var(--ink); margin: 18px 0 2px; }
.sec-sub { color: var(--ink2); font-size: .86rem; margin: 0 0 8px; }
.insight { border-radius: 14px; padding: 14px 16px; margin: 6px 0 10px; border:1px solid var(--line);
           background: #fff; border-top: 4px solid var(--accent); height: 100%; }
.insight .q { font-size: .78rem; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing:.04em; }
.insight .a { font-size: 1.02rem; font-weight: 700; color: var(--ink); margin: 4px 0; }
.insight .d { font-size: .86rem; color: var(--ink2); }
.foot { color: var(--muted); font-size: .78rem; margin-top: 28px; border-top:1px solid var(--line); padding-top:10px; }

[data-testid="stSidebar"] { background: #f4f7fc; }
.chart-title { font-size: .98rem; font-weight: 700; color: var(--ink); margin: 14px 0 6px; line-height: 1.3; }
.chart-title sup { font-weight: 500; color: var(--ink2); }
[data-testid="stPlotlyChart"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding: 6px 6px 0; }

@media (max-width: 640px) {
  .hero { padding: 16px 16px; border-radius: 14px; }
  .hero h1 { font-size: 1.25rem; }
  .kpi .value { font-size: 1.35rem; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Data (cached) + filters shared by all pages
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading supply chain data…")
def load():
    return m.load_all()


def data():
    """Filtered data for the current page, using the sidebar filter values."""
    f = st.session_state.get("filters")
    d = load()
    if not f:
        return d
    return m.filter_data(d, f["start"], f["end"], f["plants"], f["regions"])


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------
def hero(title: str, subtitle: str, tags=()):
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    st.markdown(f'<div class="hero">{tag_html}<h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def kpi(label, value, note="", accent=BLUE, status=None):
    """status: None | 'good' | 'warn' | 'bad'  -> shows a labelled pill (never color alone)."""
    pill = ""
    if status:
        text = {"good": "✓ On target", "warn": "! Watch", "bad": "✕ Off target"}[status]
        pill = f'<span class="pill {status}">{text}</span>'
    cls = "value txt" if len(str(value)) > 12 else "value"
    return (f'<div class="kpi" style="--accent:{accent}"><div class="label">{label}</div>'
            f'<div class="{cls}">{value}</div><div class="note">{pill}{note}</div></div>')


def kpi_row(cards):
    st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="sec">{title}</div>' + (f'<div class="sec-sub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def insight(question, answer, detail, accent=BLUE):
    st.markdown(f'<div class="insight" style="--accent:{accent}"><div class="q">{question}</div>'
                f'<div class="a">{answer}</div><div class="d">{detail}</div></div>', unsafe_allow_html=True)


def footer():
    st.markdown('<div class="foot">Automotive Supply Chain &amp; Quality Analytics · Portfolio project by '
                'Salma Akter · Data is synthetic and reproducible (src/generate_data.py); '
                'supplier and plant names are fictional.</div>', unsafe_allow_html=True)


def style(fig: go.Figure, height=360, legend=True, title=None):
    """Apply the shared chart style. The title is drawn as HTML above the chart (see show()),
    so a legend that wraps onto several lines on a phone can never cover it."""
    n_series = len(fig.data)
    has_legend = legend and n_series > 1
    fig.update_layout(
        height=height, template="plotly_white", title=None,
        meta={"ui_title": title or ""},
        font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif", size=12, color=INK_2),
        margin=dict(l=8, r=40, t=12, b=8),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        hoverlabel=dict(bgcolor="#ffffff", font_size=12, font_color=INK, bordercolor=AXIS),
        showlegend=has_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                    font=dict(size=11)),
        bargap=0.28,
    )
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_traces(cliponaxis=False, selector=dict(type="scatter"))
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=INK_2),
                     automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, tickfont=dict(color=MUTED),
                     title_font=dict(color=INK_2), automargin=True)
    return fig


def show(fig):
    title = (fig.layout.meta or {}).get("ui_title", "") if isinstance(fig.layout.meta, dict) else ""
    if title:
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True})


def fmt_money(x):
    x = float(x)
    if abs(x) >= 1e9:
        return f"${x/1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x/1e6:,.1f}M"
    if abs(x) >= 1e3:
        return f"${x/1e3:,.0f}K"
    return f"${x:,.0f}"


def empty_guard(df: pd.DataFrame) -> bool:
    if df is None or len(df) == 0:
        st.info("No records match the current filters. Widen the date range or clear a filter in the sidebar.")
        return True
    return False

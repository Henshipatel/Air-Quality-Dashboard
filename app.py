"""
Air Quality & Weather Correlation Dashboard
-------------------------------------------
Public, READ-ONLY Streamlit dashboard.

* Data source : weather_daily.csv, air_quality_daily.csv, cities.csv (read only)
* No uploads, no edits, no deletes, no database writes, no secrets in this file.
"""

import html
import inspect
import logging
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats

# ==========================================
# PAGE SETTINGS  (must be the first Streamlit call)
# ==========================================

st.set_page_config(
    page_title="Air Quality & Weather Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
LOGGER = logging.getLogger("aq_dashboard")


def _stretch_kwargs(func):
    """Use width="stretch" when this Streamlit version supports it, else use_container_width."""
    try:
        if "width" in inspect.signature(func).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


CHART_STRETCH = _stretch_kwargs(st.plotly_chart)
TABLE_STRETCH = _stretch_kwargs(st.dataframe)

# ==========================================
# THEME CONSTANTS
# ==========================================

FONT = "DM Sans, Segoe UI, Arial, sans-serif"
PALETTE = ["#00E5FF", "#14B8A6", "#38BDF8", "#2DD4BF", "#0EA5E9", "#5EEAD4", "#7DD3FC", "#0D9488"]
CYAN_SCALE = ["#0E7490", "#06B6D4", "#67E8F9"]
HEAT_SCALE = ["#0B2A4A", "#0E7490", "#14B8A6", "#00E5FF", "#E0FBFF"]
DIVERGING = [[0.0, "#F43F5E"], [0.5, "#0B1730"], [1.0, "#00E5FF"]]

# Indian AQI categories (CPCB bands)
AQI_BANDS = [
    ("Good", 0, 50, "#22C55E"),
    ("Satisfactory", 51, 100, "#A3E635"),
    ("Moderate", 101, 200, "#FACC15"),
    ("Poor", 201, 300, "#FB923C"),
    ("Very Poor", 301, 400, "#EF4444"),
    ("Severe", 401, 500, "#E11D48"),
]
CATEGORY_ORDER = [b[0] for b in AQI_BANDS]
CATEGORY_COLORS = {b[0]: b[3] for b in AQI_BANDS}
SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-Monsoon"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

LABELS = {
    "date": "Date",
    "city": "City",
    "region": "Region",
    "state": "State",
    "AQI": "AQI",
    "pm2_5_mean": "PM2.5 (µg/m³)",
    "pm10_mean": "PM10 (µg/m³)",
    "no2_mean": "NO₂ (µg/m³)",
    "so2_mean": "SO₂ (µg/m³)",
    "dust_mean": "Dust (µg/m³)",
    "aod_mean": "Aerosol optical depth",
    "temperature_2m_mean": "Mean temperature (°C)",
    "temperature_2m_max": "Max temperature (°C)",
    "temperature_2m_min": "Min temperature (°C)",
    "relative_humidity_2m_mean": "Mean humidity (%)",
    "wind_speed_10m_max": "Max wind speed (km/h)",
    "precipitation_sum": "Precipitation (mm)",
}

NUMERIC_VARS = [
    "AQI", "pm2_5_mean", "pm10_mean", "no2_mean", "so2_mean",
    "temperature_2m_mean", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "precipitation_sum",
]


def label(col):
    return LABELS.get(col, col)


# ==========================================
# STYLING
# ==========================================

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap');

:root {
    --bg: #050B1A;
    --panel: rgba(13, 27, 52, 0.62);
    --panel-solid: #0B1730;
    --line: rgba(56, 189, 248, 0.22);
    --cyan: #00E5FF;
    --blue: #1E90FF;
    --teal: #14B8A6;
    --text: #FFFFFF;
    --soft: #DCE6FA;
    --muted: #A9BAD6;
}

.stApp {
    font-family: 'DM Sans', 'Segoe UI', Arial, sans-serif;
    color: var(--text);
    background:
        radial-gradient(1100px 560px at 88% -8%, rgba(0, 180, 255, 0.16), transparent 60%),
        radial-gradient(900px 520px at -8% 8%, rgba(20, 184, 166, 0.12), transparent 55%),
        #050B1A;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], .stDeployButton, #MainMenu { display: none !important; }
footer { visibility: hidden; }

.block-container {
    padding: 1.6rem 2.4rem 4rem 2.4rem;
    max-width: 1500px;
}

h1, h2, h3, h4 {
    font-family: 'Sora', 'DM Sans', sans-serif;
    color: #FFFFFF !important;
    letter-spacing: -0.01em;
}

.stMarkdown p, .stMarkdown li, label, .stCaption { color: var(--soft); }
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }

:focus-visible { outline: 2px solid var(--cyan) !important; outline-offset: 2px; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #071326 0%, #08172E 55%, #06101F 100%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }

.brand {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 10px 16px 10px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 14px;
}
.brand-logo {
    width: 42px; height: 42px; border-radius: 12px;
    display: grid; place-items: center; font-size: 22px;
    background: linear-gradient(135deg, rgba(30,144,255,.35), rgba(0,229,255,.18));
    border: 1px solid rgba(0, 229, 255, .45);
    box-shadow: 0 0 18px rgba(0, 180, 255, .35);
}
.brand-name { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.05rem; color: #fff; line-height: 1.15; }
.brand-sub { color: var(--muted); font-size: .8rem; }

.side-title {
    color: var(--muted); font-size: .8rem; font-weight: 600;
    margin: 18px 4px 6px 4px;
}

[data-testid="stSidebar"] div[role="radiogroup"] { gap: 4px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label {
    width: 100%;
    padding: 9px 12px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: transparent;
    cursor: pointer;
    transition: background .18s ease, border-color .18s ease, box-shadow .18s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: rgba(0, 180, 255, .10);
    border-color: rgba(0, 229, 255, .28);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, rgba(30,144,255,.32), rgba(0,229,255,.10));
    border-color: rgba(0, 229, 255, .6);
    box-shadow: 0 0 18px rgba(0, 180, 255, .25);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    color: var(--soft) !important; font-size: .95rem; font-weight: 500;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: #FFFFFF !important; font-weight: 700;
}

.lock-note {
    margin-top: 18px; padding: 10px 12px; border-radius: 12px;
    border: 1px solid var(--line); background: rgba(13, 27, 52, .6);
    color: var(--soft); font-size: .82rem; line-height: 1.4;
}

/* ---------- Hero ---------- */
.hero {
    position: relative; overflow: hidden;
    padding: 26px 28px; margin-bottom: 20px;
    border-radius: 20px; border: 1px solid var(--line);
    background: linear-gradient(120deg, rgba(30,144,255,.24), rgba(13,27,52,.72) 55%, rgba(20,184,166,.16));
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 0 40px rgba(0, 150, 255, .10);
}
.hero-row { display: flex; align-items: center; gap: 16px; }
.hero-icon {
    flex: 0 0 auto; width: 54px; height: 54px; border-radius: 16px;
    display: grid; place-items: center; font-size: 28px;
    background: rgba(0, 229, 255, .12); border: 1px solid rgba(0, 229, 255, .45);
    box-shadow: 0 0 22px rgba(0, 180, 255, .35);
}
.hero h1 {
    margin: 0 !important; padding: 0 !important;
    font-size: clamp(1.45rem, 3vw, 2.25rem); font-weight: 800; line-height: 1.15;
}
.hero p { color: var(--soft); margin: 6px 0 0 0; max-width: 72ch; line-height: 1.5; }
.chip {
    display: inline-block; margin-top: 12px; padding: 4px 12px; border-radius: 999px;
    border: 1px solid rgba(0, 229, 255, .4); background: rgba(0, 229, 255, .08);
    color: #E6FBFF; font-size: .82rem; font-weight: 600;
}

/* ---------- KPI cards ---------- */
.kpi-grid {
    display: grid; gap: 14px; margin: 4px 0 22px 0;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}
.kpi {
    position: relative; padding: 16px 18px 16px 20px; border-radius: 16px;
    background: var(--panel); border: 1px solid var(--line);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.kpi::before {
    content: ""; position: absolute; left: 0; top: 16px; bottom: 16px;
    width: 3px; border-radius: 3px; background: var(--accent, #00E5FF);
}
.kpi:hover {
    transform: translateY(-3px); border-color: rgba(0, 229, 255, .6);
    box-shadow: 0 12px 30px rgba(0, 150, 255, .20);
}
.kpi-top { display: flex; align-items: center; gap: 10px; }
.kpi-icon {
    width: 38px; height: 38px; border-radius: 11px; font-size: 19px;
    display: grid; place-items: center;
    background: rgba(0, 229, 255, .10); border: 1px solid rgba(0, 229, 255, .30);
}
.kpi-label { color: var(--muted); font-size: .88rem; font-weight: 500; }
.kpi-value {
    margin-top: 10px; color: #FFFFFF; line-height: 1.15;
    font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.85rem;
}
.kpi-sub { margin-top: 6px; color: var(--muted); font-size: .84rem; }
.pill {
    display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px;
    border-radius: 999px; border: 1px solid var(--accent, #00E5FF);
    background: rgba(255, 255, 255, .05); color: #FFFFFF; font-size: .8rem; font-weight: 600;
}
.pill::before {
    content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--accent, #00E5FF);
}

/* ---------- Sections, insights, bands ---------- */
.section { margin: 26px 0 10px 0; }
.section h3 { margin: 0 !important; padding: 0 !important; font-size: 1.2rem; font-weight: 700; }
.section p { margin: 3px 0 0 0; color: var(--muted); font-size: .92rem; }

.insight {
    display: flex; gap: 12px; align-items: flex-start; margin: 8px 0;
    padding: 14px 16px; border-radius: 14px; line-height: 1.5; color: #EAF1FF;
    background: var(--panel); border: 1px solid var(--line);
    border-left: 3px solid var(--accent, #00E5FF);
}
.insight-icon { font-size: 1.1rem; line-height: 1.5; }

.bands { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 14px 0; }
.band {
    display: flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 10px;
    background: var(--panel); border: 1px solid var(--line); color: #FFFFFF; font-size: .86rem;
}
.band span { width: 12px; height: 12px; border-radius: 50%; }
.band em { color: var(--muted); font-style: normal; }

.info-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.info-card {
    padding: 18px 20px; border-radius: 16px; background: var(--panel);
    border: 1px solid var(--line); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
}
.info-card h4 { margin: 0 0 8px 0 !important; font-size: 1.05rem; }
.info-card p, .info-card li { color: var(--soft); line-height: 1.6; font-size: .95rem; }
.info-card ul { margin: 0; padding-left: 1.1rem; }
.tech { display: flex; flex-wrap: wrap; gap: 8px; }
.tech span {
    padding: 5px 12px; border-radius: 999px; font-size: .86rem; font-weight: 600; color: #E6FBFF;
    border: 1px solid rgba(0, 229, 255, .4); background: rgba(0, 229, 255, .08);
}

/* ---------- Charts, tables, inputs, buttons ---------- */
[data-testid="stPlotlyChart"] {
    padding: 8px 8px 2px 8px; border-radius: 16px;
    background: var(--panel); border: 1px solid var(--line);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    transition: border-color .2s ease, box-shadow .2s ease;
}
[data-testid="stPlotlyChart"]:hover {
    border-color: rgba(0, 229, 255, .5); box-shadow: 0 10px 28px rgba(0, 150, 255, .14);
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: rgba(13, 27, 52, .85) !important;
    border: 1px solid var(--line) !important; border-radius: 10px !important;
}
div[data-baseweb="select"] *, div[data-baseweb="input"] input { color: #FFFFFF !important; }

button[data-baseweb="tab"] p { color: var(--muted); font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] p { color: #FFFFFF; }

.stButton button, .stDownloadButton button {
    background: linear-gradient(90deg, #1E90FF, #00B4FF); color: #FFFFFF !important;
    border: 0; border-radius: 10px; font-weight: 600; padding: .55rem 1.2rem;
    transition: box-shadow .2s ease, transform .2s ease;
}
.stButton button p, .stDownloadButton button p { color: #FFFFFF !important; }
.stButton button:hover, .stDownloadButton button:hover {
    box-shadow: 0 0 22px rgba(0, 180, 255, .70); transform: translateY(-1px);
}

hr { border-color: var(--line) !important; }

.app-footer {
    margin-top: 40px; padding: 20px 10px 6px 10px; text-align: center;
    border-top: 1px solid var(--line); color: var(--muted); font-size: .88rem; line-height: 1.7;
}
.app-footer b { color: #FFFFFF; }

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
    .block-container { padding: 1.2rem 1.2rem 3rem 1.2rem; }
}
@media (max-width: 640px) {
    .block-container { padding: 1rem 0.8rem 3rem 0.8rem; }
    .hero { padding: 18px 16px; }
    .hero-icon { width: 44px; height: 44px; font-size: 22px; }
    .kpi-value { font-size: 1.55rem; }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
}
@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}
</style>"""


def esc(value):
    return html.escape(str(value))


def fmt(value, digits=1, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{digits}f}{suffix}"


def aqi_band(value):
    """Return (category name, colour) for an AQI value using Indian AQI bands."""
    if value is None or pd.isna(value):
        return "N/A", "#A9BAD6"
    for name, _lo, hi, colour in AQI_BANDS:
        if value <= hi:
            return name, colour
    return AQI_BANDS[-1][0], AQI_BANDS[-1][3]


def describe_corr(r):
    if r is None or pd.isna(r):
        return "could not be calculated"
    a = abs(r)
    if a < 0.2:
        strength = "very weak"
    elif a < 0.4:
        strength = "weak"
    elif a < 0.6:
        strength = "moderate"
    elif a < 0.8:
        strength = "strong"
    else:
        strength = "very strong"
    return f"{strength} {'positive' if r > 0 else 'negative'}"


# ==========================================
# UI BUILDING BLOCKS
# ==========================================

def page_header(icon, title, subtitle, chip=""):
    chip_html = f'<div class="chip">{esc(chip)}</div>' if chip else ""
    st.markdown(
        f'<div class="hero"><div class="hero-row"><div class="hero-icon">{icon}</div>'
        f"<div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div></div>{chip_html}</div>",
        unsafe_allow_html=True,
    )


def section(title, description=""):
    desc = f"<p>{esc(description)}</p>" if description else ""
    st.markdown(f'<div class="section"><h3>{esc(title)}</h3>{desc}</div>', unsafe_allow_html=True)


def kpi_card(icon, name, value, sub="", accent="#00E5FF", pill=False):
    if sub and pill:
        sub_html = f'<div class="kpi-sub"><span class="pill">{esc(sub)}</span></div>'
    elif sub:
        sub_html = f'<div class="kpi-sub">{esc(sub)}</div>'
    else:
        sub_html = ""
    return (
        f'<div class="kpi" style="--accent:{accent}">'
        f'<div class="kpi-top"><div class="kpi-icon">{icon}</div>'
        f'<div class="kpi-label">{esc(name)}</div></div>'
        f'<div class="kpi-value">{esc(value)}</div>{sub_html}</div>'
    )


def show_kpis(cards):
    st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def insight(text, accent="#00E5FF", icon="💡"):
    st.markdown(
        f'<div class="insight" style="--accent:{accent}">'
        f'<div class="insight-icon">{icon}</div><div>{esc(text)}</div></div>',
        unsafe_allow_html=True,
    )


def aqi_legend():
    items = "".join(
        f'<div class="band"><span style="background:{c}"></span><b>{n}</b><em>{lo}–{hi}</em></div>'
        for n, lo, hi, c in AQI_BANDS
    )
    st.markdown(f'<div class="bands">{items}</div>', unsafe_allow_html=True)


def table(data, **kwargs):
    st.dataframe(data, **TABLE_STRETCH, **kwargs)


def style_fig(fig, height=420):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color="#E6EEFF"),
        title=dict(font=dict(size=18, color="#FFFFFF"), x=0.01, xanchor="left"),
        colorway=PALETTE,
        height=height,
        margin=dict(l=20, r=20, t=62, b=30),
        legend=dict(title_text="", font=dict(size=12, color="#E6EEFF"), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0B1730", font_color="#FFFFFF", bordercolor="#00E5FF"),
    )
    axis_style = dict(
        gridcolor="rgba(148,180,255,0.12)",
        zerolinecolor="rgba(148,180,255,0.25)",
        linecolor="rgba(148,180,255,0.25)",
        tickfont=dict(color="#C7D5F0"),
        title_font=dict(color="#E6EEFF"),
    )
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    fig.update_coloraxes(colorbar_tickfont_color="#C7D5F0", colorbar_title_font_color="#E6EEFF")
    return fig


def show_chart(fig, height=420):
    style_fig(fig, height)
    st.plotly_chart(
        fig,
        config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
        **CHART_STRETCH,
    )


def rename_traces(fig):
    fig.for_each_trace(lambda t: t.update(name=label(t.name)))
    return fig


def monthly_mean(data, columns):
    out = data.set_index("date")[columns].resample("MS").mean()
    return out.dropna(how="all").reset_index()


def dual_axis_chart(data, left, right, title, height=420):
    m = monthly_mean(data, [left, right])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=m["date"], y=m[left], name=label(left), mode="lines",
                   line=dict(color="#00E5FF", width=3)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=m["date"], y=m[right], name=label(right), mode="lines",
                   line=dict(color="#14B8A6", width=3)),
        secondary_y=True,
    )
    fig.update_layout(title=title, hovermode="x unified")
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text=label(left), secondary_y=False)
    fig.update_yaxes(title_text=label(right), secondary_y=True, showgrid=False)
    show_chart(fig, height)


def scatter_chart(data, x, y, color, title):
    fig = px.scatter(
        data, x=x, y=y, color=color, hover_name="city", opacity=0.55,
        color_continuous_scale=CYAN_SCALE, render_mode="webgl", labels=LABELS, title=title,
    )
    fig.update_traces(marker=dict(size=5))
    show_chart(fig)


def render_footer():
    st.markdown(
        '<div class="app-footer"><b>Air Quality &amp; Weather Correlation Dashboard</b><br>'
        "Built with Python · Streamlit · Pandas · Plotly · SciPy<br>"
        "Public read-only view: visitors can explore the data but cannot change it.</div>",
        unsafe_allow_html=True,
    )


# ==========================================
# LOAD DATA  (read-only CSV files)
# ==========================================

@st.cache_data(show_spinner=False)
def load_data():
    weather = pd.read_csv(BASE_DIR / "weather_daily.csv")
    air = pd.read_csv(BASE_DIR / "air_quality_daily.csv")
    cities = pd.read_csv(BASE_DIR / "cities.csv")

    weather["date"] = pd.to_datetime(weather["date"])
    air["date"] = pd.to_datetime(air["date"])

    df = pd.merge(weather, air, on=["date", "city"], how="inner")
    df = pd.merge(df, cities, on="city", how="left")
    df = df.drop_duplicates(subset=["date", "city"])

    if "india_aqi_pm" in df.columns:
        df["AQI"] = df["india_aqi_pm"]
    else:
        df["AQI"] = df["india_aqi"]

    if "india_aqi_pm_category" in df.columns:
        df["AQI Category"] = df["india_aqi_pm_category"]
    else:
        df["AQI Category"] = df["india_aqi_category"]

    df["Season"] = df["date"].dt.month.map({
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Summer", 4: "Summer", 5: "Summer",
        6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
        10: "Post-Monsoon", 11: "Post-Monsoon",
    })
    return df.reset_index(drop=True)


def apply_filters(df, city, date_range, min_date, max_date):
    start, end = min_date, max_date
    if isinstance(date_range, (tuple, list)):
        if len(date_range) == 2:
            start, end = date_range
        elif len(date_range) == 1:
            start = date_range[0]
    elif isinstance(date_range, date):
        start = date_range

    by_date = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
    by_city = by_date if city == "All Cities" else by_date[by_date["city"] == city]
    return by_date, by_city


# ==========================================
# PAGES
# ==========================================

def page_home(ctx):
    fdf = ctx.fdf
    page_header(
        "🌍", "Air Quality & Weather Dashboard",
        "Monitor air pollution and understand how it relates to weather across Indian cities.",
        chip=ctx.coverage,
    )

    avg_aqi = fdf["AQI"].mean()
    band, colour = aqi_band(avg_aqi)
    latest = fdf["date"].max()
    latest_aqi = fdf.loc[fdf["date"] == latest, "AQI"].mean()
    l_band, l_colour = aqi_band(latest_aqi)

    show_kpis([
        kpi_card("🌫️", "Average AQI", fmt(avg_aqi), band, colour, pill=True),
        kpi_card("📅", "Latest day AQI", fmt(latest_aqi), f"{l_band} · {latest:%d %b %Y}", l_colour),
        kpi_card("🏭", "Average PM2.5", fmt(fdf["pm2_5_mean"].mean()), "µg/m³", "#14B8A6"),
        kpi_card("🌡️", "Average temperature", fmt(fdf["temperature_2m_mean"].mean(), 1, " °C"), "", "#00E5FF"),
        kpi_card("💧", "Average humidity", fmt(fdf["relative_humidity_2m_mean"].mean(), 1, " %"), "", "#38BDF8"),
        kpi_card("🗂️", "Total records", f"{len(fdf):,}", f"{fdf['city'].nunique()} cities", "#1E90FF"),
    ])

    col1, col2 = st.columns(2)

    with col1:
        cat = fdf["AQI Category"].value_counts().reset_index()
        cat.columns = ["Category", "Count"]
        fig = px.pie(
            cat, names="Category", values="Count", hole=0.55, color="Category",
            color_discrete_map=CATEGORY_COLORS, category_orders={"Category": CATEGORY_ORDER},
            title="Share of days by AQI category",
        )
        fig.update_traces(
            textinfo="percent", sort=False, textfont=dict(color="#FFFFFF", size=13),
            marker=dict(line=dict(color="#050B1A", width=2)),
        )
        show_chart(fig)

    with col2:
        daily = fdf.groupby("date", as_index=False)["AQI"].mean().sort_values("date")
        daily["rolling"] = daily["AQI"].rolling(30, min_periods=1).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["AQI"], name="Daily average AQI", mode="lines",
            line=dict(color="rgba(0,229,255,0.55)", width=1.5)))
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["rolling"], name="30-day average", mode="lines",
            line=dict(color="#14B8A6", width=3.5)))
        fig.update_layout(title="Average AQI over time", hovermode="x unified")
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="AQI")
        show_chart(fig)

    section("Weather and pollution trends", "Monthly averages for the selected cities and dates.")
    col1, col2 = st.columns(2)
    with col1:
        dual_axis_chart(fdf, "temperature_2m_mean", "relative_humidity_2m_mean",
                        "Temperature and humidity (monthly average)")
    with col2:
        m = monthly_mean(fdf, ["pm2_5_mean", "pm10_mean"])
        fig = px.line(m, x="date", y=["pm2_5_mean", "pm10_mean"],
                      title="Air pollution trend (monthly average)",
                      labels={"value": "Concentration (µg/m³)", "date": "Month"})
        rename_traces(fig)
        fig.update_traces(line=dict(width=3))
        fig.update_layout(hovermode="x unified")
        show_chart(fig)

    section("City-wise average AQI")
    city_data = (
        fdf.groupby("city", as_index=False)["AQI"].mean().sort_values("AQI", ascending=False)
    )
    fig = px.bar(city_data, x="city", y="AQI", color="AQI", color_continuous_scale=CYAN_SCALE,
                 title="Average AQI by city", labels=LABELS)
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(tickangle=-45, title_text="City")
    show_chart(fig, 460)

    section("Key insights", "Calculated from the selected data. Correlation does not prove causation.")
    if len(city_data) > 1:
        top, low = city_data.iloc[0], city_data.iloc[-1]
        insight(f"{top['city']} has the highest average AQI ({top['AQI']:.1f}); "
                f"{low['city']} has the lowest ({low['AQI']:.1f}).", "#FB923C", "🏙️")
    season_mean = fdf.groupby("Season")["AQI"].mean().dropna()
    if len(season_mean) > 1:
        insight(f"{season_mean.idxmax()} has the highest average AQI ({season_mean.max():.1f}); "
                f"{season_mean.idxmin()} has the lowest ({season_mean.min():.1f}).", "#00E5FF", "🍃")
    r_t = fdf["temperature_2m_mean"].corr(fdf["AQI"])
    r_h = fdf["relative_humidity_2m_mean"].corr(fdf["AQI"])
    insight(f"Temperature and AQI show a {describe_corr(r_t)} relationship (r = {fmt(r_t, 2)}). "
            f"Humidity and AQI show a {describe_corr(r_h)} relationship (r = {fmt(r_h, 2)}).",
            "#14B8A6", "🔗")


def page_air_quality(ctx):
    fdf, city = ctx.fdf, ctx.city
    page_header("🌫️", "Air Quality Analysis", "Explore pollution levels and pollutant trends.", ctx.coverage)

    avg_aqi = fdf["AQI"].mean()
    band, colour = aqi_band(avg_aqi)
    peak = fdf.loc[fdf["AQI"].idxmax()]
    low = fdf.loc[fdf["AQI"].idxmin()]
    show_kpis([
        kpi_card("🌫️", "Average AQI", fmt(avg_aqi, 2), band, colour, pill=True),
        kpi_card("🔺", "Maximum AQI", fmt(peak["AQI"], 0), f"{peak['city']} · {peak['date']:%d %b %Y}", "#EF4444"),
        kpi_card("🔻", "Minimum AQI", fmt(low["AQI"], 0), f"{low['city']} · {low['date']:%d %b %Y}", "#22C55E"),
        kpi_card("🏭", "Average PM2.5", fmt(fdf["pm2_5_mean"].mean(), 1), "µg/m³", "#14B8A6"),
    ])

    section("AQI scale", "Indian AQI categories used in this dashboard.")
    aqi_legend()

    pollutants = ["pm2_5_mean", "pm10_mean", "no2_mean", "so2_mean", "dust_mean", "aod_mean"]
    available = [x for x in pollutants if x in fdf.columns]

    col_a, col_b = st.columns([2, 1])
    pollutant = col_a.selectbox("Select pollutant", available, format_func=label, key="aq_pollutant")
    per_city = False
    if city == "All Cities":
        per_city = col_b.checkbox("Show every city separately", value=False, key="aq_per_city")

    if city == "All Cities" and not per_city:
        series = fdf.groupby("date", as_index=False)[pollutant].mean().sort_values("date")
        fig = px.line(series, x="date", y=pollutant, labels=LABELS,
                      title=f"{label(pollutant)} trend (average of all selected cities)")
    elif city == "All Cities":
        fig = px.line(fdf.sort_values("date"), x="date", y=pollutant, color="city",
                      render_mode="webgl", labels=LABELS, title=f"{label(pollutant)} trend by city")
    else:
        fig = px.line(fdf.sort_values("date"), x="date", y=pollutant, labels=LABELS,
                      title=f"{label(pollutant)} trend: {city}")
    fig.update_traces(line=dict(width=2))
    fig.update_layout(hovermode="x unified" if not per_city else "closest")
    show_chart(fig)

    col1, col2 = st.columns(2)
    with col1:
        cat = fdf["AQI Category"].value_counts().reindex(CATEGORY_ORDER).dropna().reset_index()
        cat.columns = ["Category", "Days"]
        fig = px.bar(cat, x="Category", y="Days", color="Category", color_discrete_map=CATEGORY_COLORS,
                     title="Days in each AQI category")
        fig.update_layout(showlegend=False)
        show_chart(fig, 380)
    with col2:
        dom = fdf["dominant_pollutant"].value_counts().reset_index()
        dom.columns = ["Pollutant", "Days"]
        fig = px.bar(dom, x="Pollutant", y="Days", title="Dominant pollutant (all-pollutant AQI)",
                     color_discrete_sequence=["#00E5FF"])
        show_chart(fig, 380)
        st.caption("Dominant pollutant comes from the all-pollutant India AQI column in your data.")

    section("Pollutant statistics")
    table(fdf[available].describe().round(2).rename(columns=LABELS))


def page_weather(ctx):
    fdf, city = ctx.fdf, ctx.city
    page_header("🌡️", "Weather Analysis", "Understand weather patterns and how they relate to air quality.", ctx.coverage)

    show_kpis([
        kpi_card("🌡️", "Average temperature", fmt(fdf["temperature_2m_mean"].mean(), 1, " °C"), "", "#00E5FF"),
        kpi_card("🔥", "Highest temperature", fmt(fdf["temperature_2m_max"].max(), 1, " °C"), "", "#FB923C"),
        kpi_card("💧", "Average humidity", fmt(fdf["relative_humidity_2m_mean"].mean(), 1, " %"), "", "#38BDF8"),
        kpi_card("💨", "Average max wind", fmt(fdf["wind_speed_10m_max"].mean(), 1, " km/h"), "", "#14B8A6"),
        kpi_card("🌧️", "Avg daily rainfall", fmt(fdf["precipitation_sum"].mean(), 2, " mm"), "", "#1E90FF"),
    ])

    dual_axis_chart(fdf, "temperature_2m_mean", "relative_humidity_2m_mean",
                    "Temperature and humidity (monthly average)", 440)

    weather_columns = [
        "temperature_2m_mean", "temperature_2m_max", "temperature_2m_min",
        "relative_humidity_2m_mean", "wind_speed_10m_max", "precipitation_sum",
    ]
    available = [x for x in weather_columns if x in fdf.columns]

    col_a, col_b = st.columns([2, 1])
    selected = col_a.selectbox("Select weather parameter", available, format_func=label, key="wx_param")
    per_city = False
    if city == "All Cities":
        per_city = col_b.checkbox("Show every city separately", value=False, key="wx_per_city")

    if city == "All Cities" and not per_city:
        series = fdf.groupby("date", as_index=False)[selected].mean().sort_values("date")
        fig = px.line(series, x="date", y=selected, labels=LABELS,
                      title=f"{label(selected)} (average of all selected cities)")
    elif city == "All Cities":
        fig = px.line(fdf.sort_values("date"), x="date", y=selected, color="city",
                      render_mode="webgl", labels=LABELS, title=f"{label(selected)} by city")
    else:
        fig = px.line(fdf.sort_values("date"), x="date", y=selected, labels=LABELS,
                      title=f"{label(selected)}: {city}")
    fig.update_traces(line=dict(width=2))
    show_chart(fig)

    section("Weather vs air quality", "Each point is one city on one day.")
    col1, col2 = st.columns(2)
    with col1:
        scatter_chart(fdf, "temperature_2m_mean", "AQI", "AQI", "Temperature vs AQI")
    with col2:
        scatter_chart(fdf, "relative_humidity_2m_mean", "AQI", "AQI", "Humidity vs AQI")
    scatter_chart(fdf, "temperature_2m_mean", "pm2_5_mean", "pm2_5_mean", "Temperature vs PM2.5")


def page_city_comparison(ctx):
    sub_all = ctx.date_df
    page_header("🏙️", "City Comparison", "Compare air quality and weather across cities. Uses the date range from the sidebar.",
                ctx.coverage)

    available_cities = sorted(sub_all["city"].dropna().unique().tolist())
    defaults = [c for c in ["Delhi", "Mumbai", "Ahmedabad", "Bengaluru"] if c in available_cities]
    if len(defaults) < 2:
        defaults = available_cities[:3]

    chosen = st.multiselect("Select cities to compare (choose 2 or more)", available_cities,
                            default=defaults, key="cmp_cities")

    if len(chosen) < 2:
        st.info("Select at least two cities to see the comparison.")
    else:
        sub = sub_all[sub_all["city"].isin(chosen)]
        summary = sub.groupby("city").agg(**{
            "Average AQI": ("AQI", "mean"),
            "PM2.5 (µg/m³)": ("pm2_5_mean", "mean"),
            "PM10 (µg/m³)": ("pm10_mean", "mean"),
            "Temperature (°C)": ("temperature_2m_mean", "mean"),
            "Humidity (%)": ("relative_humidity_2m_mean", "mean"),
            "Wind (km/h)": ("wind_speed_10m_max", "mean"),
            "Rain (mm/day)": ("precipitation_sum", "mean"),
        }).reset_index().rename(columns={"city": "City"}).sort_values("Average AQI", ascending=False)

        worst, best = summary.iloc[0], summary.iloc[-1]
        w_band, w_col = aqi_band(worst["Average AQI"])
        b_band, b_col = aqi_band(best["Average AQI"])
        show_kpis([
            kpi_card("🔺", "Highest AQI in selection", worst["City"], f"{worst['Average AQI']:.1f} · {w_band}", w_col, pill=True),
            kpi_card("🔻", "Lowest AQI in selection", best["City"], f"{best['Average AQI']:.1f} · {b_band}", b_col, pill=True),
            kpi_card("🏙️", "Cities compared", str(len(chosen)), "", "#00E5FF"),
            kpi_card("📏", "AQI gap", fmt(worst["Average AQI"] - best["Average AQI"]), "highest minus lowest", "#14B8A6"),
        ])

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(summary, x="City", y="Average AQI", color="Average AQI",
                         color_continuous_scale=CYAN_SCALE, title="Average AQI")
            fig.update_layout(coloraxis_showscale=False)
            show_chart(fig, 400)
        with col2:
            long = summary.melt(id_vars="City", value_vars=["PM2.5 (µg/m³)", "PM10 (µg/m³)"],
                                var_name="Pollutant", value_name="Concentration (µg/m³)")
            fig = px.bar(long, x="City", y="Concentration (µg/m³)", color="Pollutant", barmode="group",
                         color_discrete_sequence=["#00E5FF", "#14B8A6"], title="PM2.5 and PM10")
            show_chart(fig, 400)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(summary, x="City", y="Temperature (°C)", title="Average temperature",
                         color_discrete_sequence=["#00E5FF"])
            show_chart(fig, 380)
        with col2:
            fig = px.bar(summary, x="City", y="Humidity (%)", title="Average humidity",
                         color_discrete_sequence=["#14B8A6"])
            show_chart(fig, 380)

        section("Trend over time", "Monthly average for the selected cities.")
        metric_options = [c for c in NUMERIC_VARS if c in sub.columns]
        metric = st.selectbox("Select metric", metric_options, format_func=label, key="cmp_metric")
        trend = (sub.groupby(["city", pd.Grouper(key="date", freq="MS")])[metric].mean()
                 .dropna().reset_index())
        fig = px.line(trend, x="date", y=metric, color="city", labels=LABELS,
                      title=f"{label(metric)}: monthly average by city")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(hovermode="x unified")
        show_chart(fig, 440)

        section("Summary table")
        table(summary.round(2), hide_index=True)

    section("All-city ranking", "Average AQI across every city for the selected dates.")
    rank = sub_all.groupby("city", as_index=False)["AQI"].mean().sort_values("AQI", ascending=False)
    n = min(10, len(rank))
    col1, col2 = st.columns(2)
    with col1:
        top = rank.head(n).sort_values("AQI")
        fig = px.bar(top, x="AQI", y="city", orientation="h", labels=LABELS,
                     title=f"{n} most polluted cities", color_discrete_sequence=["#00E5FF"])
        show_chart(fig, 420)
    with col2:
        bottom = rank.tail(n).sort_values("AQI", ascending=False)
        fig = px.bar(bottom, x="AQI", y="city", orientation="h", labels=LABELS,
                     title=f"{n} cleanest cities", color_discrete_sequence=["#14B8A6"])
        show_chart(fig, 420)


def page_data_viz(ctx):
    fdf, sub_all = ctx.fdf, ctx.date_df
    page_header("📉", "Data Visualization", "Interactive maps, heatmaps and a chart builder.", ctx.coverage)

    tab_map, tab_heat, tab_region, tab_build = st.tabs(
        ["🗺️ City map", "🔥 Seasonal heatmap", "🧭 Regions", "🛠️ Chart builder"]
    )

    with tab_map:
        st.caption("Shows every city for the selected dates (the sidebar city filter is not applied).")
        m = (sub_all.groupby(["city", "state", "region", "latitude", "longitude"], as_index=False)["AQI"]
             .mean())
        if m.empty:
            st.info("No city coordinates are available for the selected dates.")
        else:
            fig = px.scatter_geo(
                m, lat="latitude", lon="longitude", size="AQI", color="AQI", hover_name="city",
                hover_data={"state": True, "region": True, "AQI": ":.1f", "latitude": False, "longitude": False},
                color_continuous_scale=CYAN_SCALE, size_max=24, scope="asia",
                title="Average AQI by city",
            )
            fig.update_geos(
                fitbounds="locations", showcountries=True, countrycolor="#2A4A7F",
                showland=True, landcolor="#0B1730", showocean=True, oceancolor="#050B1A",
                showcoastlines=True, coastlinecolor="#2A4A7F", showlakes=False,
                bgcolor="rgba(0,0,0,0)", showframe=False,
            )
            show_chart(fig, 560)

    with tab_heat:
        st.caption("Average AQI for each city by calendar month (selected dates, all cities).")
        tmp = sub_all.assign(month=sub_all["date"].dt.month)
        pivot = tmp.pivot_table(index="city", columns="month", values="AQI", aggfunc="mean")
        pivot = pivot.reindex(columns=range(1, 13))
        pivot.columns = MONTHS
        pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale=HEAT_SCALE,
                        labels=dict(x="Month", y="City", color="Avg AQI"),
                        title="Average AQI by city and month")
        show_chart(fig, max(520, 22 * len(pivot) + 120))

    with tab_region:
        st.caption("Distribution of daily AQI by region (selected dates, all cities).")
        fig = px.box(sub_all.dropna(subset=["region"]), x="region", y="AQI", color="region",
                     points=False, labels=LABELS, title="AQI distribution by region")
        fig.update_layout(showlegend=False)
        show_chart(fig, 460)

    with tab_build:
        st.caption("Uses the city and date filters from the sidebar.")
        numeric = [c for c in NUMERIC_VARS if c in fdf.columns]
        kind = st.selectbox("Chart type", ["Scatter", "Monthly trend", "Histogram", "Box plot"], key="cb_kind")
        group_map = {"None": None, "Season": "Season", "Region": "region"}

        if kind == "Scatter":
            c1, c2, c3 = st.columns(3)
            x = c1.selectbox("X axis", numeric, index=numeric.index("temperature_2m_mean"),
                             format_func=label, key="cb_sx")
            y = c2.selectbox("Y axis", numeric, index=0, format_func=label, key="cb_sy")
            g = c3.selectbox("Colour by", list(group_map), key="cb_sg")
            fig = px.scatter(fdf, x=x, y=y, color=group_map[g], hover_name="city", opacity=0.5,
                             render_mode="webgl", labels=LABELS, color_discrete_sequence=PALETTE,
                             title=f"{label(y)} vs {label(x)}")
            fig.update_traces(marker=dict(size=5))
        elif kind == "Monthly trend":
            c1, c2 = st.columns(2)
            y = c1.selectbox("Variable", numeric, index=0, format_func=label, key="cb_ty")
            g = c2.selectbox("Group by", ["None", "Region"], key="cb_tg")
            if g == "Region":
                t = (fdf.dropna(subset=["region"]).groupby(["region", pd.Grouper(key="date", freq="MS")])[y]
                     .mean().dropna().reset_index())
                fig = px.line(t, x="date", y=y, color="region", labels=LABELS,
                              title=f"{label(y)}: monthly average by region")
            else:
                t = monthly_mean(fdf, [y])
                fig = px.line(t, x="date", y=y, labels=LABELS, title=f"{label(y)}: monthly average")
            fig.update_traces(line=dict(width=3))
            fig.update_layout(hovermode="x unified")
        elif kind == "Histogram":
            c1, c2 = st.columns(2)
            x = c1.selectbox("Variable", numeric, index=0, format_func=label, key="cb_hx")
            g = c2.selectbox("Group by", list(group_map), key="cb_hg")
            fig = px.histogram(fdf, x=x, color=group_map[g], nbins=40, barmode="overlay", opacity=0.75,
                               labels=LABELS, color_discrete_sequence=PALETTE,
                               title=f"Distribution of {label(x)}")
            fig.update_yaxes(title_text="Number of records")
        else:
            c1, c2 = st.columns(2)
            y = c1.selectbox("Variable", numeric, index=0, format_func=label, key="cb_by")
            g = c2.selectbox("Group by", ["Season", "Region"], key="cb_bg")
            gcol = group_map[g]
            fig = px.box(fdf.dropna(subset=[gcol]), x=gcol, y=y, color=gcol, points=False, labels=LABELS,
                         category_orders={"Season": SEASON_ORDER}, title=f"{label(y)} by {g.lower()}")
            fig.update_layout(showlegend=False)
        show_chart(fig, 480)


def page_correlation(ctx):
    fdf = ctx.fdf
    page_header("🔗", "Correlation Analysis", "Study relationships between weather and air pollution.", ctx.coverage)

    variables = [
        "AQI", "pm2_5_mean", "pm10_mean", "no2_mean", "so2_mean", "temperature_2m_mean",
        "relative_humidity_2m_mean", "wind_speed_10m_max", "precipitation_sum",
    ]
    available = [x for x in variables if x in fdf.columns]
    pearson = fdf[available].corr(method="pearson")
    spearman = fdf[available].corr(method="spearman")

    weather_vars = [v for v in available if v in
                    ("temperature_2m_mean", "relative_humidity_2m_mean", "wind_speed_10m_max", "precipitation_sum")]
    if "AQI" in pearson.index and weather_vars:
        cards = []
        for v in weather_vars:
            r = pearson.loc["AQI", v]
            cards.append(kpi_card("🔗", f"AQI vs {label(v).split(' (')[0].lower()}", fmt(r, 2),
                                  describe_corr(r), "#00E5FF"))
        show_kpis(cards)

    def pretty(m):
        return m.rename(index=LABELS, columns=LABELS)

    section("Pearson correlation matrix", "Linear relationships. Cyan means positive, red means negative.")
    fig = px.imshow(pretty(pearson), text_auto=".2f", color_continuous_scale=DIVERGING,
                    zmin=-1, zmax=1, title="Pearson correlation")
    show_chart(fig, 560)

    section("Spearman correlation matrix", "Rank-based relationships that do not need to be linear.")
    fig = px.imshow(pretty(spearman), text_auto=".2f", color_continuous_scale=DIVERGING,
                    zmin=-1, zmax=1, title="Spearman correlation")
    show_chart(fig, 560)

    insight("Pearson measures linear relationships. Spearman measures rank-based (monotonic) relationships. "
            "Correlation does not prove causation.", "#14B8A6", "ℹ️")


def page_seasonal(ctx):
    fdf = ctx.fdf
    page_header("🍃", "Seasonal Analysis", "Compare air quality across seasons.", ctx.coverage)

    seasonal = fdf.groupby("Season")["AQI"].agg(["mean", "median", "count"])
    seasonal = seasonal.reindex([s for s in SEASON_ORDER if s in seasonal.index]).reset_index()
    seasonal.columns = ["Season", "Mean AQI", "Median AQI", "Records"]

    cards = []
    for _, row in seasonal.iterrows():
        b, c = aqi_band(row["Mean AQI"])
        cards.append(kpi_card("🍃", f"{row['Season']} average AQI", fmt(row["Mean AQI"]), b, c, pill=True))
    show_kpis(cards)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(seasonal, x="Season", y="Mean AQI", color="Mean AQI", color_continuous_scale=CYAN_SCALE,
                     category_orders={"Season": SEASON_ORDER}, title="Average AQI by season")
        fig.update_layout(coloraxis_showscale=False)
        show_chart(fig, 420)
    with col2:
        fig = px.box(fdf, x="Season", y="AQI", color="Season", category_orders={"Season": SEASON_ORDER},
                     title="Seasonal AQI distribution", color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False)
        show_chart(fig, 420)

    section("Seasonal AQI summary")
    table(seasonal.round(2), hide_index=True)

    groups = [g["AQI"].dropna() for _, g in fdf.groupby("Season")]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) >= 2:
        h_stat, p_value = stats.kruskal(*groups)
        section("Kruskal-Wallis test", "Tests whether AQI differs between seasons.")
        show_kpis([
            kpi_card("📐", "H statistic", f"{h_stat:.3f}", "", "#00E5FF"),
            kpi_card("🎯", "P value", f"{p_value:.5f}", "", "#14B8A6"),
        ])
        if p_value < 0.05:
            insight("AQI differences between seasons are statistically significant (p < 0.05).", "#22C55E", "✅")
        else:
            insight("No statistically significant seasonal difference was detected (p ≥ 0.05).", "#FACC15", "ℹ️")
        st.caption("With very large samples, even small differences can be significant. "
                   "Look at the average AQI values above as well.")


def page_outliers(ctx):
    fdf = ctx.fdf
    page_header("📊", "Outlier Detection", "Identify unusual AQI values using the IQR method.", ctx.coverage)

    aq = fdf["AQI"].dropna()
    q1, q3 = aq.quantile(0.25), aq.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = fdf[(fdf["AQI"] < lower) | (fdf["AQI"] > upper)]

    show_kpis([
        kpi_card("⬇️", "Lower limit", fmt(lower, 2), "", "#38BDF8"),
        kpi_card("⬆️", "Upper limit", fmt(upper, 2), "", "#FB923C"),
        kpi_card("⚠️", "Total outliers", f"{len(outliers):,}", f"{len(outliers) / max(len(fdf), 1):.1%} of records", "#EF4444"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        fig = px.box(fdf, y="AQI", title="AQI box plot", color_discrete_sequence=["#00E5FF"])
        show_chart(fig, 420)
    with col2:
        by_city = outliers.groupby("city").size().sort_values(ascending=False).head(15).reset_index()
        by_city.columns = ["City", "Outliers"]
        if by_city.empty:
            st.info("No outliers were found for the selected filters.")
        else:
            fig = px.bar(by_city, x="City", y="Outliers", title="Cities with the most outliers",
                         color_discrete_sequence=["#14B8A6"])
            fig.update_xaxes(tickangle=-45)
            show_chart(fig, 420)

    section("Outlier records", "The 100 highest outlier values.")
    shown = outliers.sort_values("AQI", ascending=False)[["date", "city", "AQI"]].head(100).copy()
    shown["date"] = shown["date"].dt.strftime("%Y-%m-%d")
    table(shown, hide_index=True)


def page_statistics(ctx):
    fdf = ctx.fdf
    page_header("📈", "Statistical Testing", "Descriptive statistics and AQI distribution.", ctx.coverage)

    aq = fdf["AQI"].dropna()
    mode = aq.mode()
    show_kpis([
        kpi_card("➗", "Mean", fmt(aq.mean(), 2), "", "#00E5FF"),
        kpi_card("➖", "Median", fmt(aq.median(), 2), "", "#14B8A6"),
        kpi_card("🔢", "Mode", fmt(mode.iloc[0], 2) if not mode.empty else "N/A", "", "#38BDF8"),
        kpi_card("↔️", "Std deviation", fmt(aq.std(), 2), "", "#1E90FF"),
        kpi_card("📐", "Skewness", fmt(aq.skew(), 3), "", "#5EEAD4"),
    ])

    fig = px.histogram(fdf, x="AQI", nbins=40, title="AQI frequency distribution",
                       color_discrete_sequence=["#00E5FF"])
    fig.update_yaxes(title_text="Number of records")
    show_chart(fig, 440)

    section("Complete descriptive statistics")
    table(fdf.select_dtypes(include="number").describe().round(2))


def page_cleaning(ctx):
    fdf = ctx.fdf
    page_header("📁", "Data Cleaning", "Check missing values and duplicate records.", ctx.coverage)

    show_kpis([
        kpi_card("🕳️", "Total missing values", f"{int(fdf.isnull().sum().sum()):,}", "", "#FB923C"),
        kpi_card("🧬", "Duplicate records", f"{int(fdf.duplicated().sum()):,}", "", "#EF4444"),
        kpi_card("🗂️", "Records checked", f"{len(fdf):,}", f"{fdf.shape[1]} columns", "#00E5FF"),
    ])

    section("Missing values by column")
    missing = fdf.isnull().sum().reset_index()
    missing.columns = ["Column", "Missing Values"]
    missing["Missing %"] = (missing["Missing Values"] / max(len(fdf), 1) * 100).round(2)
    table(missing, hide_index=True)

    section("Cleaned data preview", "First 100 rows after removing duplicates.")
    cleaned = fdf.drop_duplicates().copy()
    table(cleaned.head(100))

    st.download_button(
        "⬇️ Download cleaned dataset",
        data=cleaned.to_csv(index=False).encode("utf-8"),
        file_name="cleaned_air_quality_data.csv",
        mime="text/csv",
    )
    st.caption("This downloads a copy of the filtered data. It does not change the dashboard's source files.")


def page_lagged(ctx):
    fdf = ctx.fdf
    page_header("⏳", "Lagged Correlation", "Is the previous day's weather related to today's air quality?", ctx.coverage)

    lag = fdf.sort_values(["city", "date"]).copy()
    lag["prev_date"] = lag.groupby("city")["date"].shift(1)
    lag["Previous day temperature"] = lag.groupby("city")["temperature_2m_mean"].shift(1)
    lag["Previous day humidity"] = lag.groupby("city")["relative_humidity_2m_mean"].shift(1)
    # Keep only rows where the previous record is exactly one day earlier.
    lag = lag[(lag["date"] - lag["prev_date"]).dt.days == 1]
    lag = lag.dropna(subset=["Previous day temperature", "Previous day humidity", "AQI"])

    if len(lag) <= 2:
        st.warning("There is not enough consecutive-day data for lagged analysis. Widen the date range.")
        return

    t_corr = lag["Previous day temperature"].corr(lag["AQI"])
    h_corr = lag["Previous day humidity"].corr(lag["AQI"])
    show_kpis([
        kpi_card("🌡️", "Previous-day temperature vs AQI", fmt(t_corr, 3), describe_corr(t_corr), "#00E5FF"),
        kpi_card("💧", "Previous-day humidity vs AQI", fmt(h_corr, 3), describe_corr(h_corr), "#14B8A6"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        scatter_chart(lag, "Previous day temperature", "AQI", "AQI", "Previous-day temperature vs today's AQI")
    with col2:
        scatter_chart(lag, "Previous day humidity", "AQI", "AQI", "Previous-day humidity vs today's AQI")


def page_about(ctx):
    df = ctx.df
    page_header("ℹ️", "About Project", "Air Quality & Weather Correlation Dashboard", ctx.coverage)

    start, end = df["date"].min(), df["date"].max()
    show_kpis([
        kpi_card("🏙️", "Cities", f"{df['city'].nunique()}", "", "#00E5FF"),
        kpi_card("🗂️", "Records", f"{len(df):,}", "daily city readings", "#14B8A6"),
        kpi_card("📅", "Period", f"{start:%b %Y} – {end:%b %Y}", "", "#38BDF8"),
        kpi_card("🧮", "Columns", f"{df.shape[1]}", "after merging", "#1E90FF"),
    ])

    st.markdown(
        '<div class="info-grid">'
        '<div class="info-card"><h4>🎯 Project overview</h4>'
        "<p>This project studies air pollution and weather conditions across Indian cities. "
        "It helps users understand how temperature, humidity, wind and rainfall are related to air quality.</p></div>"
        '<div class="info-card"><h4>🧭 Objectives</h4><ul>'
        "<li>Analyze the Air Quality Index (AQI)</li>"
        "<li>Compare AQI across cities</li>"
        "<li>Study seasonal air quality changes</li>"
        "<li>Identify unusual pollution values (outliers)</li>"
        "<li>Analyze how temperature, humidity and AQI relate</li>"
        "<li>Perform statistical analysis</li></ul></div>"
        '<div class="info-card"><h4>🛠️ Technologies</h4><div class="tech">'
        "<span>Python</span><span>Streamlit</span><span>Pandas</span><span>Plotly</span>"
        "<span>SciPy</span><span>SQL</span></div></div>"
        '<div class="info-card"><h4>📚 Dataset</h4><ul>'
        "<li><b>weather_daily.csv</b>: daily weather per city</li>"
        "<li><b>air_quality_daily.csv</b>: daily pollutants and AQI per city</li>"
        "<li><b>cities.csv</b>: state, region and coordinates</li>"
        "<li>Weather and air-quality records are joined on date and city. "
        "Air-quality records start in " + esc(f"{start:%B %Y}") + ".</li></ul></div>"
        '<div class="info-card"><h4>🧪 Methods</h4><ul>'
        "<li>AQI shown in the dashboard is the PM-based India AQI from your data</li>"
        "<li>Seasons: Winter (Dec–Feb), Summer (Mar–May), Monsoon (Jun–Sep), Post-Monsoon (Oct–Nov)</li>"
        "<li>Outliers use the IQR method (1.5 × IQR)</li>"
        "<li>Season differences use the Kruskal-Wallis test</li>"
        "<li>Lagged correlation compares yesterday's weather with today's AQI</li></ul></div>"
        '<div class="info-card"><h4>🔒 Data protection</h4>'
        "<p>This is a public, read-only dashboard. Visitors can filter and explore the data, "
        "but cannot upload files, edit records, delete data or access any admin function.</p></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    section("Dashboard pages")
    st.markdown(
        '<div class="info-card"><ul>'
        "<li><b>Home</b>: AQI and weather summary cards, trends and key insights</li>"
        "<li><b>Air Quality Analysis</b> and <b>Weather Analysis</b>: detailed trends and scatter plots</li>"
        "<li><b>City Comparison</b>: side-by-side comparison and city rankings</li>"
        "<li><b>Data Visualization</b>: map, heatmap, regions and a chart builder</li>"
        "<li><b>Correlation</b>, <b>Seasonal</b>, <b>Outlier</b>, <b>Statistical</b>, <b>Cleaning</b> "
        "and <b>Lagged Correlation</b>: the analysis modules</li></ul></div>",
        unsafe_allow_html=True,
    )


# ==========================================
# MAIN
# ==========================================

PAGES = {
    "🏠 Home": page_home,
    "🌫️ Air Quality Analysis": page_air_quality,
    "🌡️ Weather Analysis": page_weather,
    "🏙️ City Comparison": page_city_comparison,
    "📉 Data Visualization": page_data_viz,
    "🔗 Correlation Analysis": page_correlation,
    "🍃 Seasonal Analysis": page_seasonal,
    "📊 Outlier Detection": page_outliers,
    "📈 Statistical Testing": page_statistics,
    "📁 Data Cleaning": page_cleaning,
    "⏳ Lagged Correlation": page_lagged,
    "ℹ️ About Project": page_about,
}


def main():
    st.markdown(CSS, unsafe_allow_html=True)

    try:
        df = load_data()
    except Exception:
        # Full details go to the server log only; visitors see a short message.
        LOGGER.exception("Could not load the data files")
        st.error("The data could not be loaded. Please check that weather_daily.csv, "
                 "air_quality_daily.csv and cities.csv are in the same folder as app.py.")
        st.stop()

    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-logo">🌍</div><div>'
            '<div class="brand-name">AQ Dashboard</div>'
            '<div class="brand-sub">Air Quality &amp; Weather</div></div></div>',
            unsafe_allow_html=True,
        )
        page = st.radio("Navigation", list(PAGES), label_visibility="collapsed", key="nav_page")

        st.markdown('<div class="side-title">Filter data</div>', unsafe_allow_html=True)
        city_list = ["All Cities"] + sorted(df["city"].dropna().unique().tolist())
        selected_city = st.selectbox("Select city", city_list, key="f_city")

        min_date, max_date = df["date"].min().date(), df["date"].max().date()
        date_range = st.date_input("Select date range", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date, key="f_dates")
        if isinstance(date_range, (tuple, list)) and len(date_range) == 1:
            st.caption("Pick an end date to complete the range.")

        st.markdown(
            '<div class="lock-note">🔒 Read-only dashboard. Filters change the view only. '
            "No data can be edited or uploaded.</div>",
            unsafe_allow_html=True,
        )

    date_df, fdf = apply_filters(df, selected_city, date_range, min_date, max_date)

    ctx = SimpleNamespace(
        df=df, date_df=date_df, fdf=fdf, city=selected_city,
        coverage=f"📅 Data: {min_date:%d %b %Y} – {max_date:%d %b %Y}  ·  Showing: {selected_city}",
    )

    if fdf.empty and page != "ℹ️ About Project":
        page_header("🔎", "No data for these filters", "Choose a different city or widen the date range in the sidebar.")
        render_footer()
        st.stop()

    PAGES[page](ctx)
    render_footer()


main()
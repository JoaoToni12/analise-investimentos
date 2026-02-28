"""Design system: colors, Plotly layout, CSS, and reusable UI components."""

from __future__ import annotations

import streamlit as st

COLORS = {
    "primary": "#0066FF",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "muted": "#6B7280",
    "text": "#FAFAFA",
    "text_secondary": "#8B8D97",
    "card_bg": "#1A1D23",
    "card_border": "#2D3139",
    "bg_dark": "#0E1117",
}

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, system-ui, sans-serif", "color": "#FAFAFA", "size": 12},
    "colorway": ["#0066FF", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899"],
}

CLASS_COLORS = {
    "ACAO": "#0066FF",
    "FII": "#F59E0B",
    "ETF": "#22C55E",
    "BDR": "#EF4444",
    "CRYPTO": "#8B5CF6",
    "TESOURO": "#06B6D4",
    "RENDA_FIXA_PRIVADA": "#EC4899",
}

CLASS_LABELS = {
    "ACAO": "Ações",
    "FII": "FIIs",
    "ETF": "ETFs",
    "BDR": "BDRs",
    "CRYPTO": "Crypto",
    "TESOURO": "Tesouro Direto",
    "RENDA_FIXA_PRIVADA": "Renda Fixa",
}

CSS = """
<style>
    div[data-testid="stMetric"] {
        background-color: #1A1D23;
        border: 1px solid #2D3139;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #8B8D97;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background-color: #1A1D23; border-radius: 8px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; padding: 8px 14px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #0066FF !important; }
    section[data-testid="stSidebar"] { background-color: #0A0D12; border-right: 1px solid #2D3139; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", positive: bool = True, icon: str = "") -> None:
    """Render a styled KPI card."""
    delta_html = ""
    if delta:
        color = COLORS["success"] if positive else COLORS["danger"]
        arrow = "↑" if positive else "↓"
        delta_html = f'<div style="font-size:0.82rem;color:{color};margin-top:4px;">{arrow} {delta}</div>'

    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#1A1D23,#22252D);border:1px solid #2D3139;
        border-radius:10px;padding:18px 22px;height:120px;">
        <div style="font-size:0.7rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;">
            {icon} {label}</div>
        <div style="font-size:1.6rem;font-weight:700;color:#FAFAFA;margin-top:6px;">{value}</div>
        {delta_html}</div>""",
        unsafe_allow_html=True,
    )


def signal_strip(n_buy: int, n_hold: int, n_sell: int) -> None:
    """Render a visual BUY/HOLD/SELL signal bar."""
    total = n_buy + n_hold + n_sell
    if total == 0:
        return

    def _bar(count: int, label: str, bg: str, border: str, text_color: str, bar_color: str) -> str:
        pct = count / total * 100
        return f"""<div style="flex:1;background:{bg};border:1px solid {border};border-radius:8px;
        padding:10px 14px;text-align:center;">
        <div style="font-size:1.8rem;font-weight:800;color:{text_color};">{count}</div>
        <div style="font-size:0.7rem;color:{text_color};opacity:0.8;text-transform:uppercase;
        letter-spacing:0.05em;">{label}</div>
        <div style="width:100%;background:#1A1D23;border-radius:4px;height:3px;margin-top:6px;">
        <div style="width:{pct}%;background:{bar_color};height:3px;border-radius:4px;"></div>
        </div></div>"""

    buy = _bar(n_buy, "Comprar", "#0D2818", "#166534", "#22C55E", "#22C55E")
    hold = _bar(n_hold, "Manter", "#1A1D23", "#2D3139", "#8B8D97", "#6B7280")
    sell = _bar(n_sell, "Vender", "#1C0F12", "#7F1D1D", "#EF4444", "#EF4444")

    html = f'<div style="display:flex;gap:10px;margin:8px 0 16px 0;">{buy}{hold}{sell}</div>'
    st.markdown(html, unsafe_allow_html=True)

from __future__ import annotations

import logging

import numpy as np
import streamlit as st

from config import NON_BRAPI_PREFIXES
from engine.grey_zones import classify_all
from engine.markowitz import (
    compute_covariance_matrix,
    compute_expected_returns,
    compute_log_returns,
    generate_efficient_frontier,
    optimize_portfolio,
    suggest_targets,
)
from engine.models import Asset, AssetClass
from engine.portfolio import compute_weights, enrich_weights
from engine.rebalancer import compute_rebalancing
from ingestion.brapi_client import get_batch_quotes
from ingestion.portfolio_loader import load_portfolio, load_portfolio_meta
from ingestion.tesouro_client import get_tesouro_prices
from ingestion.yfinance_client import STABLECOINS, get_yfinance_quotes
from ui.action_table import render_action_table
from ui.charts import (
    render_allocation_chart,
    render_class_allocation_pie,
    render_correlation_heatmap,
    render_deviation_chart,
    render_efficient_frontier,
    render_maturity_calendar,
)
from ui.dashboard import render_dashboard
from ui.portfolio_manager import render_portfolio_manager
from ui.reserves import get_reserve_value, render_capital_allocation, render_emergency_reserve
from ui.sidebar import render_sidebar
from ui.theme import inject_css

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Rebalanceamento de Carteira", page_icon="📈", layout="wide")
inject_css()

st.markdown(
    '<h1 style="font-size:1.8rem;margin-bottom:0;">📈 Rebalanceamento de Carteira</h1>',
    unsafe_allow_html=True,
)
st.caption("Motor analítico com Markowitz, zonas cinzentas e rebalanceamento inteligente")

params = render_sidebar()

with st.expander("🗂️ Gestão da Carteira", expanded=False):
    render_portfolio_manager()

positions = load_portfolio()
portfolio_meta = load_portfolio_meta()

if not positions:
    st.warning("Nenhuma posição cadastrada. Abra 'Gestão da Carteira' acima para adicionar.")
    st.stop()

# --- Classify tickers by pricing source ---
brapi_tickers, yf_crypto_tickers, tesouro_tickers = [], [], []
for p in positions:
    t, cls = p["ticker"], p.get("asset_class", "ACAO")
    if t.startswith("TESOURO_"):
        tesouro_tickers.append(t)
    elif cls == "CRYPTO":
        yf_crypto_tickers.append(t)
    elif not any(t.startswith(pf) for pf in NON_BRAPI_PREFIXES):
        brapi_tickers.append(t)

all_tickers = [p["ticker"] for p in positions]
asset_classes = [p.get("asset_class", "ACAO") for p in positions]


@st.cache_data(ttl=300, show_spinner="Buscando cotações B3...")
def _fetch_brapi(tl: tuple[str, ...]) -> dict[str, float]:
    return get_batch_quotes(list(tl))


@st.cache_data(ttl=600, show_spinner="Buscando preços crypto...")
def _fetch_yf(tl: tuple[str, ...], cl: tuple[str, ...]) -> dict[str, float]:
    return get_yfinance_quotes(list(tl), list(cl))


@st.cache_data(ttl=3600, show_spinner="Buscando preços Tesouro...")
def _fetch_tesouro() -> dict[str, float]:
    return get_tesouro_prices()


@st.cache_data(ttl=3600, show_spinner="Baixando histórico...")
def _fetch_hist(tl: tuple[str, ...], cl: tuple[str, ...], period: str) -> dict:
    from ingestion.yfinance_client import get_historical_prices

    return {"df": get_historical_prices(list(tl), list(cl), period)}


# --- Fetch prices ---
if params["refresh"] or "quotes" not in st.session_state:
    q: dict[str, float] = {}
    if brapi_tickers:
        q.update(_fetch_brapi(tuple(brapi_tickers)))
    if yf_crypto_tickers:
        cc = tuple(p.get("asset_class", "CRYPTO") for p in positions if p["ticker"] in yf_crypto_tickers)
        q.update(_fetch_yf(tuple(yf_crypto_tickers), cc))
    if tesouro_tickers:
        q.update(_fetch_tesouro())
    st.session_state["quotes"] = q

quotes = st.session_state.get("quotes", {})

# --- Build assets ---
assets: list[Asset] = []
for p in positions:
    ticker = p["ticker"]
    price = quotes.get(ticker, 0.0)
    if price <= 0:
        price = float(p.get("current_price", 0.0))
    if price <= 0:
        price = float(p.get("avg_price", 0.0))
    assets.append(
        Asset(
            ticker=ticker,
            asset_class=AssetClass.from_str(p.get("asset_class", "ACAO")),
            quantity=float(p.get("quantity", 0)),
            avg_price=float(p.get("avg_price", 0)),
            current_price=price,
            target_weight=float(p.get("target_weight_pct", 0)),
        )
    )

assets = enrich_weights(assets)
zones = classify_all(assets, params["relative_band"], params["absolute_band"])

# --- Reserve ---
target_reserve = params["monthly_expenses"] * params["emergency_months"]
current_reserve = get_reserve_value(portfolio_meta)
reserve_deficit = max(target_reserve - current_reserve, 0)

# --- Markowitz ---
MARKOWITZ_CLASSES = {"ACAO", "FII", "ETF", "BDR", "CRYPTO"}
mk_pairs = [(t, c) for t, c in zip(all_tickers, asset_classes) if c in MARKOWITZ_CLASSES and t not in STABLECOINS]
mk_tickers = [t for t, _ in mk_pairs]
mk_classes = [c for _, c in mk_pairs]

hist_data = _fetch_hist(tuple(mk_tickers), tuple(mk_classes), "2y") if mk_tickers else {}
prices_df = hist_data.get("df")
frontier, optimal, current_point, corr_matrix = [], None, None, np.array([])

if prices_df is not None and not prices_df.empty and len(prices_df.columns) >= 2:
    returns_df = compute_log_returns(prices_df)
    if not returns_df.empty and len(returns_df.columns) >= 2:
        mu = compute_expected_returns(returns_df)
        sigma = compute_covariance_matrix(returns_df)
        frontier = generate_efficient_frontier(mu, sigma)
        optimal = optimize_portfolio(mu, sigma, params["risk_free_rate"])

        w_arr = np.array([compute_weights(assets).get(t, 0) / 100.0 for t in prices_df.columns])
        if len(w_arr) == len(mu):
            current_point = {
                "return": float(w_arr @ mu),
                "volatility": float(np.sqrt(w_arr @ sigma @ w_arr)),
            }
        corr_matrix = returns_df.corr().values

        if optimal is not None:
            cur_w = compute_weights(assets)
            subset_share = sum(cur_w.get(t, 0) for t in prices_df.columns)
            scale = subset_share / 100.0 if subset_share > 0 else 1.0
            opt_w = {t: float(w) * 100 * scale for t, w in zip(prices_df.columns, optimal["weights"])}
            suggested = suggest_targets(cur_w, opt_w, params["blend_factor"])
            for a in assets:
                if a.ticker in suggested:
                    a.target_weight = suggested[a.ticker]
            zones = classify_all(assets, params["relative_band"], params["absolute_band"])

# --- Capital allocation + Rebalancing (compute before rendering) ---
to_reserve, to_invest = render_capital_allocation(params["cash_injection"], reserve_deficit)
orders, residual_cash = compute_rebalancing(assets, to_invest, zones, max_orders=params["max_orders"])

# --- Dashboard (uses real orders for signal strip) ---
render_dashboard(assets, zones, portfolio_meta, orders)

# --- Tabs ---
tab_orders, tab_reserve, tab_alloc, tab_frontier, tab_rf, tab_corr = st.tabs(
    ["📋 Ordens", "🛡️ Reserva", "📊 Alocação", "📈 Fronteira", "🏦 Renda Fixa", "🔗 Correlação"]
)

with tab_orders:
    render_action_table(assets, zones, orders, residual_cash)

with tab_reserve:
    render_emergency_reserve(portfolio_meta, params["monthly_expenses"], params["emergency_months"])

with tab_alloc:
    render_class_allocation_pie(assets)
    render_allocation_chart(assets)
    render_deviation_chart(assets, zones)

with tab_frontier:
    render_efficient_frontier(frontier, optimal, current_point)

with tab_rf:
    render_maturity_calendar(positions)

with tab_corr:
    if corr_matrix.size > 0:
        render_correlation_heatmap(corr_matrix, list(prices_df.columns))
    else:
        st.info("Dados históricos insuficientes para a matriz de correlação.")

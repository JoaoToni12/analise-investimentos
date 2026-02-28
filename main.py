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
from ingestion.portfolio_loader import load_portfolio
from ingestion.yfinance_client import get_historical_prices
from ui.action_table import render_action_table
from ui.charts import (
    render_allocation_chart,
    render_correlation_heatmap,
    render_deviation_chart,
    render_efficient_frontier,
)
from ui.dashboard import render_dashboard
from ui.portfolio_manager import render_portfolio_manager
from ui.reserves import compute_reserve_value, render_capital_allocation, render_emergency_reserve
from ui.sidebar import render_sidebar

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Rebalanceamento de Carteira",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Sistema de Rebalanceamento de Carteira")

# --- Sidebar ---
params = render_sidebar()

# --- Portfolio Management (expander) ---
with st.expander("🗂️ Gestão da Carteira", expanded=False):
    positions = render_portfolio_manager()

positions = load_portfolio()

if not positions:
    st.warning("Nenhuma posição cadastrada. Adicione ativos na seção 'Gestão da Carteira' acima.")
    st.stop()

# --- Separate brapi-eligible tickers from manual-priced ones ---
brapi_tickers = []
for p in positions:
    ticker = p["ticker"]
    if not any(ticker.startswith(prefix) for prefix in NON_BRAPI_PREFIXES):
        brapi_tickers.append(ticker)

all_tickers = [p["ticker"] for p in positions]
asset_classes = [p.get("asset_class", "ACAO") for p in positions]


@st.cache_data(ttl=300, show_spinner="Buscando cotações...")
def _fetch_quotes(ticker_list: tuple[str, ...]) -> dict[str, float]:
    return get_batch_quotes(list(ticker_list))


@st.cache_data(ttl=3600, show_spinner="Baixando histórico de preços...")
def _fetch_historical(ticker_list: tuple[str, ...], classes: tuple[str, ...], period: str) -> dict:
    df = get_historical_prices(list(ticker_list), list(classes), period)
    return {"df": df}


if params["refresh"] or "quotes" not in st.session_state:
    if brapi_tickers:
        st.session_state["quotes"] = _fetch_quotes(tuple(brapi_tickers))
    else:
        st.session_state["quotes"] = {}

quotes = st.session_state.get("quotes", {})

# --- Build Asset objects with fallback pricing ---
assets: list[Asset] = []
for p in positions:
    ticker = p["ticker"]
    # Priority: brapi quote > stored current_price > avg_price
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

# --- Grey Zones ---
zones = classify_all(assets, params["relative_band"], params["absolute_band"])

# --- Emergency Reserve Calculations ---
target_reserve = params["monthly_expenses"] * params["emergency_months"]
current_reserve = compute_reserve_value(assets, positions)
reserve_deficit = max(target_reserve - current_reserve, 0)

# --- Markowitz (only for tickers with historical data) ---
markowitz_tickers = [t for t, c in zip(all_tickers, asset_classes) if c in ("ACAO", "FII", "ETF", "BDR")]
markowitz_classes = [c for c in asset_classes if c in ("ACAO", "FII", "ETF", "BDR")]

hist_data = {}
if markowitz_tickers:
    hist_data = _fetch_historical(tuple(markowitz_tickers), tuple(markowitz_classes), "2y")

prices_df = hist_data.get("df")
frontier: list[dict] = []
optimal: dict | None = None
current_portfolio_point: dict | None = None
corr_matrix = np.array([])

if prices_df is not None and not prices_df.empty and len(prices_df.columns) >= 2:
    returns_df = compute_log_returns(prices_df)
    if not returns_df.empty:
        mu = compute_expected_returns(returns_df)
        sigma = compute_covariance_matrix(returns_df)

        frontier = generate_efficient_frontier(mu, sigma)
        optimal = optimize_portfolio(mu, sigma, params["risk_free_rate"])

        weights_arr = np.array([compute_weights(assets).get(t, 0) / 100.0 for t in prices_df.columns])
        if len(weights_arr) == len(mu):
            curr_ret = float(weights_arr @ mu)
            curr_vol = float(np.sqrt(weights_arr @ sigma @ weights_arr))
            current_portfolio_point = {"return": curr_ret, "volatility": curr_vol}

        corr_matrix = returns_df.corr().values

        if optimal is not None:
            current_w = compute_weights(assets)
            optimal_w = {t: float(w) * 100 for t, w in zip(prices_df.columns, optimal["weights"])}
            suggested = suggest_targets(current_w, optimal_w, params["blend_factor"])
            for a in assets:
                if a.ticker in suggested:
                    a.target_weight = suggested[a.ticker]
            zones = classify_all(assets, params["relative_band"], params["absolute_band"])

# --- Render UI ---
render_dashboard(assets, zones)

# --- Tabs ---
tab_capital, tab_reserve, tab_actions, tab_frontier, tab_alloc, tab_corr = st.tabs(
    [
        "💰 Capital",
        "🛡️ Reserva",
        "📋 Ordens",
        "📈 Fronteira",
        "📊 Alocação",
        "🔗 Correlação",
    ]
)

with tab_capital:
    to_reserve, to_invest = render_capital_allocation(params["cash_injection"], reserve_deficit)
    if to_invest > 0:
        orders, residual_cash = compute_rebalancing(assets, to_invest, zones)
    else:
        orders, residual_cash = [], params["cash_injection"]

with tab_reserve:
    render_emergency_reserve(assets, positions, params["monthly_expenses"], params["emergency_months"])

with tab_actions:
    effective_cash = to_invest if "to_invest" in dir() else params["cash_injection"]
    if not orders:
        orders, residual_cash = compute_rebalancing(assets, effective_cash, zones)
    render_action_table(assets, zones, orders, residual_cash)

with tab_frontier:
    render_efficient_frontier(frontier, optimal, current_portfolio_point)

with tab_alloc:
    render_allocation_chart(assets)
    render_deviation_chart(assets, zones)

with tab_corr:
    if corr_matrix.size > 0:
        render_correlation_heatmap(corr_matrix, list(prices_df.columns))
    else:
        st.info("Dados históricos insuficientes para a matriz de correlação.")

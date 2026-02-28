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
from ingestion.tesouro_client import get_tesouro_prices
from ingestion.yfinance_client import get_yfinance_quotes
from ui.action_table import render_action_table
from ui.charts import (
    render_allocation_chart,
    render_class_allocation_pie,
    render_correlation_heatmap,
    render_deviation_chart,
    render_efficient_frontier,
)
from ui.dashboard import render_dashboard
from ui.portfolio_manager import render_portfolio_manager
from ui.reserves import compute_reserve_value, render_capital_allocation, render_emergency_reserve
from ui.sidebar import render_sidebar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Rebalanceamento de Carteira",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Sistema de Rebalanceamento de Carteira")

params = render_sidebar()

with st.expander("🗂️ Gestão da Carteira", expanded=False):
    render_portfolio_manager()

positions = load_portfolio()

if not positions:
    st.warning("Nenhuma posição cadastrada. Adicione ativos na seção 'Gestão da Carteira' acima.")
    st.stop()

# --- Classify tickers by pricing source ---
brapi_tickers: list[str] = []
yf_crypto_tickers: list[str] = []
tesouro_tickers: list[str] = []
manual_tickers: list[str] = []

for p in positions:
    t = p["ticker"]
    cls = p.get("asset_class", "ACAO")
    if t.startswith("TESOURO_"):
        tesouro_tickers.append(t)
    elif cls == "CRYPTO":
        yf_crypto_tickers.append(t)
    elif any(t.startswith(prefix) for prefix in NON_BRAPI_PREFIXES):
        manual_tickers.append(t)
    else:
        brapi_tickers.append(t)

all_tickers = [p["ticker"] for p in positions]
asset_classes = [p.get("asset_class", "ACAO") for p in positions]


# --- Pricing functions ---
@st.cache_data(ttl=300, show_spinner="Buscando cotações B3...")
def _fetch_brapi(ticker_list: tuple[str, ...]) -> dict[str, float]:
    return get_batch_quotes(list(ticker_list))


@st.cache_data(ttl=600, show_spinner="Buscando preços crypto...")
def _fetch_yf_quotes(ticker_list: tuple[str, ...], classes: tuple[str, ...]) -> dict[str, float]:
    return get_yfinance_quotes(list(ticker_list), list(classes))


@st.cache_data(ttl=3600, show_spinner="Buscando preços Tesouro Direto...")
def _fetch_tesouro() -> dict[str, float]:
    return get_tesouro_prices()


@st.cache_data(ttl=3600, show_spinner="Baixando histórico de preços...")
def _fetch_historical(ticker_list: tuple[str, ...], classes: tuple[str, ...], period: str) -> dict:
    from ingestion.yfinance_client import get_historical_prices as _ghp

    df = _ghp(list(ticker_list), list(classes), period)
    return {"df": df}


# --- Fetch all prices ---
if params["refresh"] or "quotes" not in st.session_state:
    all_quotes: dict[str, float] = {}
    if brapi_tickers:
        all_quotes.update(_fetch_brapi(tuple(brapi_tickers)))
    if yf_crypto_tickers:
        crypto_classes = tuple(p.get("asset_class", "CRYPTO") for p in positions if p["ticker"] in yf_crypto_tickers)
        all_quotes.update(_fetch_yf_quotes(tuple(yf_crypto_tickers), crypto_classes))
    if tesouro_tickers:
        all_quotes.update(_fetch_tesouro())
    st.session_state["quotes"] = all_quotes

quotes = st.session_state.get("quotes", {})

# --- Build Asset objects ---
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

# --- Emergency Reserve ---
target_reserve = params["monthly_expenses"] * params["emergency_months"]
current_reserve = compute_reserve_value(assets, positions)
reserve_deficit = max(target_reserve - current_reserve, 0)

# --- Markowitz (ações + FIIs + crypto with history) ---
MARKOWITZ_CLASSES = {"ACAO", "FII", "ETF", "BDR", "CRYPTO"}
markowitz_pairs = [(t, c) for t, c in zip(all_tickers, asset_classes) if c in MARKOWITZ_CLASSES]
markowitz_tickers = [t for t, _ in markowitz_pairs]
markowitz_classes = [c for _, c in markowitz_pairs]

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
    if not returns_df.empty and len(returns_df.columns) >= 2:
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

# --- Dashboard KPIs ---
render_dashboard(assets, zones)

# --- Capital allocation ---
to_reserve, to_invest = render_capital_allocation(params["cash_injection"], reserve_deficit)

# --- Rebalancing ---
orders, residual_cash = compute_rebalancing(assets, to_invest, zones)

# --- Tabs ---
tab_actions, tab_reserve, tab_frontier, tab_alloc, tab_corr = st.tabs(
    ["📋 Ordens", "🛡️ Reserva", "📈 Fronteira", "📊 Alocação", "🔗 Correlação"]
)

with tab_actions:
    render_action_table(assets, zones, orders, residual_cash)

with tab_reserve:
    render_emergency_reserve(assets, positions, params["monthly_expenses"], params["emergency_months"])

with tab_frontier:
    render_efficient_frontier(frontier, optimal, current_portfolio_point)

with tab_alloc:
    render_class_allocation_pie(assets)
    render_allocation_chart(assets)
    render_deviation_chart(assets, zones)

with tab_corr:
    if corr_matrix.size > 0:
        render_correlation_heatmap(corr_matrix, list(prices_df.columns))
    else:
        st.info("Dados históricos insuficientes para a matriz de correlação.")

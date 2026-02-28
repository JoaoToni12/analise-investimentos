from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.models import Asset, AssetClass, Band, ZoneStatus
from engine.portfolio import compute_class_weights
from engine.rebalancer import compute_class_targets

CLASS_COLORS = {
    AssetClass.ACAO: "#1f77b4",
    AssetClass.FII: "#ff7f0e",
    AssetClass.ETF: "#2ca02c",
    AssetClass.BDR: "#d62728",
    AssetClass.CRYPTO: "#9467bd",
    AssetClass.TESOURO: "#8c564b",
    AssetClass.RENDA_FIXA_PRIVADA: "#e377c2",
}

CLASS_LABELS = {
    AssetClass.ACAO: "Ações",
    AssetClass.FII: "FIIs",
    AssetClass.ETF: "ETFs",
    AssetClass.BDR: "BDRs",
    AssetClass.CRYPTO: "Crypto",
    AssetClass.TESOURO: "Tesouro",
    AssetClass.RENDA_FIXA_PRIVADA: "RF Privada",
}


def render_class_allocation_pie(assets: list[Asset]) -> None:
    """Donut chart showing class-level allocation: current vs target."""
    if not assets:
        return

    st.subheader("Alocação por Classe de Ativo")

    class_w = compute_class_weights(assets)
    class_t = compute_class_targets(assets)
    classes = [cls for cls in AssetClass if class_w.get(cls, 0) > 0 or class_t.get(cls, 0) > 0]

    labels = [CLASS_LABELS.get(c, c.value) for c in classes]
    current_vals = [class_w.get(c, 0) for c in classes]
    target_vals = [class_t.get(c, 0) for c in classes]
    colors = [CLASS_COLORS.get(c, "#999999") for c in classes]

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=current_vals,
                hole=0.45,
                marker={"colors": colors},
                textinfo="label+percent",
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Atual",
            height=350,
            margin={"t": 40, "b": 10, "l": 10, "r": 10},
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=target_vals,
                hole=0.45,
                marker={"colors": colors},
                textinfo="label+percent",
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Alvo",
            height=350,
            margin={"t": 40, "b": 10, "l": 10, "r": 10},
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_efficient_frontier(
    frontier: list[dict],
    optimal: dict | None = None,
    current_portfolio: dict | None = None,
) -> None:
    """Plot the efficient frontier."""
    if not frontier:
        st.info("Dados insuficientes para gerar a fronteira eficiente. Necessário pelo menos 2 ativos com histórico.")
        return

    st.subheader("Fronteira Eficiente de Markowitz")

    vols = [p["volatility"] * 100 for p in frontier]
    rets = [p["return"] * 100 for p in frontier]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=vols,
            y=rets,
            mode="lines",
            name="Fronteira Eficiente",
            line={"color": "#1f77b4", "width": 3},
        )
    )

    if optimal:
        fig.add_trace(
            go.Scatter(
                x=[optimal["volatility"] * 100],
                y=[optimal["return"] * 100],
                mode="markers+text",
                name="Portfólio Ótimo (Max Sharpe)",
                marker={"size": 14, "color": "#2ca02c", "symbol": "star"},
                text=[f"Sharpe: {optimal.get('sharpe', 0):.2f}"],
                textposition="top center",
            )
        )

    if current_portfolio:
        fig.add_trace(
            go.Scatter(
                x=[current_portfolio["volatility"] * 100],
                y=[current_portfolio["return"] * 100],
                mode="markers+text",
                name="Sua Carteira Atual",
                marker={"size": 14, "color": "#d62728", "symbol": "diamond"},
                text=["Atual"],
                textposition="top center",
            )
        )

    fig.update_layout(
        xaxis_title="Volatilidade Anualizada (%)",
        yaxis_title="Retorno Esperado Anualizado (%)",
        template="plotly_white",
        height=500,
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_allocation_chart(assets: list[Asset]) -> None:
    """Grouped bar chart: current vs target allocation per asset."""
    if not assets:
        return

    st.subheader("Alocação Individual: Atual vs Alvo")

    sorted_assets = sorted(assets, key=lambda a: -a.current_weight)
    tickers = [a.ticker for a in sorted_assets]
    current = [a.current_weight for a in sorted_assets]
    target = [a.target_weight for a in sorted_assets]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Atual (%)", x=tickers, y=current, marker_color="#1f77b4"))
    fig.add_trace(go.Bar(name="Alvo (%)", x=tickers, y=target, marker_color="#ff7f0e", opacity=0.7))
    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=450,
        yaxis_title="Peso (%)",
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_deviation_chart(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> None:
    """Horizontal bar chart: deviation per asset with zone coloring."""
    if not assets:
        return

    st.subheader("Desvio por Ativo (vs Zona Cinzenta)")

    sorted_assets = sorted(assets, key=lambda a: a.current_weight - a.target_weight)
    tickers = []
    deviations = []
    colors = []
    hover_texts = []

    color_map = {ZoneStatus.BUY: "#2ca02c", ZoneStatus.HOLD: "#7f7f7f", ZoneStatus.SELL: "#d62728"}

    for a in sorted_assets:
        status, band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        dev = a.current_weight - a.target_weight
        tickers.append(a.ticker)
        deviations.append(dev)
        colors.append(color_map.get(status, "#7f7f7f"))
        band_str = f"[{band.lower_bound:.2f}%, {band.upper_bound:.2f}%]" if band else ""
        hover_texts.append(f"{a.ticker}: {dev:+.2f}pp | Banda: {band_str} | {status.value}")

    fig = go.Figure(
        go.Bar(
            x=deviations,
            y=tickers,
            orientation="h",
            marker_color=colors,
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        xaxis_title="Desvio (pp)",
        template="plotly_white",
        height=max(350, len(tickers) * 28),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_heatmap(corr_matrix: np.ndarray, tickers: list[str]) -> None:
    """Heatmap of the asset correlation matrix."""
    if corr_matrix.size == 0:
        return

    st.subheader("Matriz de Correlação")
    fig = go.Figure(
        go.Heatmap(
            z=corr_matrix,
            x=tickers,
            y=tickers,
            colorscale="RdBu_r",
            zmin=-1,
            zmax=1,
            text=np.round(corr_matrix, 2),
            texttemplate="%{text}",
        )
    )
    fig.update_layout(template="plotly_white", height=max(400, len(tickers) * 35))
    st.plotly_chart(fig, use_container_width=True)

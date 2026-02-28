from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.models import Asset, Band, ZoneStatus


def render_efficient_frontier(
    frontier: list[dict],
    optimal: dict | None = None,
    current_portfolio: dict | None = None,
) -> None:
    """Plot the efficient frontier with current and optimal portfolio positions."""
    if not frontier:
        st.info("Dados insuficientes para gerar a fronteira eficiente.")
        return

    st.subheader("Fronteira Eficiente de Markowitz")

    vols = [p["volatility"] for p in frontier]
    rets = [p["return"] for p in frontier]

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
                x=[optimal["volatility"]],
                y=[optimal["return"]],
                mode="markers+text",
                name="Portfólio Ótimo",
                marker={"size": 14, "color": "#2ca02c", "symbol": "star"},
                text=["Ótimo"],
                textposition="top center",
            )
        )

    if current_portfolio:
        fig.add_trace(
            go.Scatter(
                x=[current_portfolio["volatility"]],
                y=[current_portfolio["return"]],
                mode="markers+text",
                name="Portfólio Atual",
                marker={"size": 14, "color": "#d62728", "symbol": "diamond"},
                text=["Atual"],
                textposition="top center",
            )
        )

    fig.update_layout(
        xaxis_title="Volatilidade (anualizada)",
        yaxis_title="Retorno Esperado (anualizado)",
        template="plotly_white",
        height=500,
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_allocation_chart(assets: list[Asset]) -> None:
    """Side-by-side bar chart: current vs target allocation."""
    if not assets:
        return

    st.subheader("Alocação Atual vs Alvo")

    tickers = [a.ticker for a in assets]
    current = [a.current_weight for a in assets]
    target = [a.target_weight for a in assets]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Atual (%)", x=tickers, y=current, marker_color="#1f77b4"))
    fig.add_trace(go.Bar(name="Alvo (%)", x=tickers, y=target, marker_color="#ff7f0e"))
    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=400,
        yaxis_title="Peso (%)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_deviation_chart(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> None:
    """Horizontal bar chart showing weight deviation per asset with zone coloring."""
    if not assets:
        return

    st.subheader("Desvio por Ativo (vs Zona Cinzenta)")

    tickers = []
    deviations = []
    colors = []

    for a in assets:
        status, _band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        dev = a.current_weight - a.target_weight
        tickers.append(a.ticker)
        deviations.append(dev)
        color_map = {ZoneStatus.BUY: "#2ca02c", ZoneStatus.HOLD: "#7f7f7f", ZoneStatus.SELL: "#d62728"}
        colors.append(color_map.get(status, "#7f7f7f"))

    fig = go.Figure(
        go.Bar(
            x=deviations,
            y=tickers,
            orientation="h",
            marker_color=colors,
        )
    )
    fig.update_layout(
        xaxis_title="Desvio (pp)",
        template="plotly_white",
        height=max(300, len(tickers) * 30),
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
    fig.update_layout(template="plotly_white", height=500)
    st.plotly_chart(fig, use_container_width=True)

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.models import Asset, AssetClass, Band, ZoneStatus
from engine.portfolio import compute_class_weights
from engine.rebalancer import compute_class_targets
from ui.theme import CLASS_COLORS, CLASS_LABELS, PLOTLY_LAYOUT


def render_class_allocation_pie(assets: list[Asset]) -> None:
    """Single donut with total in center + horizontal divergence bars."""
    if not assets:
        return

    st.subheader("Alocação por Classe: Atual vs Alvo")

    class_w = compute_class_weights(assets)
    class_t = compute_class_targets(assets)
    classes = [cls for cls in AssetClass if class_w.get(cls, 0) > 0 or class_t.get(cls, 0) > 0]

    labels = [CLASS_LABELS.get(c.value, c.value) for c in classes]
    current_vals = [class_w.get(c, 0) for c in classes]
    target_vals = [class_t.get(c, 0) for c in classes]
    deviations = [c - t for c, t in zip(current_vals, target_vals)]
    colors = [CLASS_COLORS.get(c.value, "#999") for c in classes]
    dev_colors = ["#22C55E" if d >= 0 else "#EF4444" for d in deviations]

    total_value = sum(a.current_value for a in assets)

    col_pie, col_bar = st.columns([2, 3])

    with col_pie:
        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=current_vals,
                hole=0.55,
                marker={"colors": colors},
                textinfo="label+percent",
                textposition="outside",
            )
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=350,
            margin={"t": 20, "b": 10, "l": 10, "r": 10},
            showlegend=False,
            annotations=[
                {
                    "text": f"R$ {total_value:,.0f}",
                    "x": 0.5,
                    "y": 0.5,
                    "font_size": 15,
                    "showarrow": False,
                    "font_color": "#FAFAFA",
                }
            ],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_bar:
        fig = go.Figure(
            go.Bar(
                x=deviations,
                y=labels,
                orientation="h",
                marker_color=dev_colors,
                text=[f"{d:+.1f}pp" for d in deviations],
                textposition="outside",
            )
        )
        fig.add_vline(x=0, line_dash="dash", line_color="#6B7280")
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=350,
            title="Desvio da Meta por Classe",
            xaxis={"title": "Sobre-alocado ← → Sub-alocado"},
            margin={"t": 50, "b": 40, "l": 120, "r": 40},
        )
        st.plotly_chart(fig, use_container_width=True)


def render_efficient_frontier(
    frontier: list[dict],
    optimal: dict | None = None,
    current_portfolio: dict | None = None,
) -> None:
    """Efficient frontier with current and optimal portfolio positions."""
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
            line={"color": "#0066FF", "width": 3},
        )
    )

    if optimal:
        fig.add_trace(
            go.Scatter(
                x=[optimal["volatility"] * 100],
                y=[optimal["return"] * 100],
                mode="markers+text",
                name=f"Ótimo (Sharpe {optimal.get('sharpe', 0):.2f})",
                marker={"size": 14, "color": "#22C55E", "symbol": "star"},
                text=["Ótimo"],
                textposition="top center",
            )
        )

    if current_portfolio:
        fig.add_trace(
            go.Scatter(
                x=[current_portfolio["volatility"] * 100],
                y=[current_portfolio["return"] * 100],
                mode="markers+text",
                name="Sua Carteira",
                marker={"size": 14, "color": "#EF4444", "symbol": "diamond"},
                text=["Atual"],
                textposition="top center",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=500,
        xaxis_title="Volatilidade Anualizada (%)",
        yaxis_title="Retorno Esperado Anualizado (%)",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_allocation_chart(assets: list[Asset]) -> None:
    """Grouped bar chart: current vs target allocation sorted by weight."""
    if not assets:
        return

    st.subheader("Alocação Individual: Atual vs Alvo")

    sorted_assets = sorted(assets, key=lambda a: -a.current_weight)[:15]
    tickers = [a.ticker for a in sorted_assets]
    current = [a.current_weight for a in sorted_assets]
    target = [a.target_weight for a in sorted_assets]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Atual (%)", x=tickers, y=current, marker_color="#0066FF"))
    fig.add_trace(go.Bar(name="Alvo (%)", x=tickers, y=target, marker_color="#F59E0B", opacity=0.7))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        barmode="group",
        yaxis_title="Peso (%)",
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_deviation_chart(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> None:
    """Horizontal deviation bars with zone coloring and hover."""
    if not assets:
        return

    st.subheader("Desvio por Ativo (vs Zona Cinzenta)")

    sorted_assets = sorted(assets, key=lambda a: a.current_weight - a.target_weight)
    color_map = {ZoneStatus.BUY: "#22C55E", ZoneStatus.HOLD: "#6B7280", ZoneStatus.SELL: "#EF4444"}

    tickers, devs, colors, hovers = [], [], [], []
    for a in sorted_assets:
        status, band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        dev = a.current_weight - a.target_weight
        tickers.append(a.ticker)
        devs.append(dev)
        colors.append(color_map.get(status, "#6B7280"))
        band_str = f"[{band.lower_bound:.1f}%, {band.upper_bound:.1f}%]" if band else ""
        hovers.append(f"{a.ticker}: {dev:+.2f}pp | Banda: {band_str} | {status.value}")

    fig = go.Figure(
        go.Bar(
            x=devs,
            y=tickers,
            orientation="h",
            marker_color=colors,
            hovertext=hovers,
            hoverinfo="text",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=max(350, len(tickers) * 26), xaxis_title="Desvio (pp)")
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_heatmap(corr_matrix: np.ndarray, tickers: list[str]) -> None:
    """Correlation heatmap with insights panel."""
    if corr_matrix.size == 0:
        return

    st.subheader("Matriz de Correlação")

    col_heat, col_insights = st.columns([3, 1])

    with col_heat:
        fig = go.Figure(
            go.Heatmap(
                z=corr_matrix,
                x=tickers,
                y=tickers,
                colorscale=[[0, "#EF4444"], [0.5, "#1A1D23"], [1, "#22C55E"]],
                zmin=-1,
                zmax=1,
                text=np.round(corr_matrix, 2),
                texttemplate="%{text}",
                textfont={"size": 9},
            )
        )
        fig.update_layout(**PLOTLY_LAYOUT, height=max(400, len(tickers) * 32))
        st.plotly_chart(fig, use_container_width=True)

    with col_insights:
        st.markdown("##### Insights")
        n = len(tickers)
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((tickers[i], tickers[j], corr_matrix[i][j]))

        high_corr = sorted(pairs, key=lambda x: -abs(x[2]))[:3]
        low_corr = sorted(pairs, key=lambda x: x[2])[:3]

        st.caption("🔗 Mais correlacionados")
        for a, b, c in high_corr:
            st.write(f"**{a}** ↔ **{b}**: {c:.2f}")

        st.caption("🔀 Mais diversificados")
        for a, b, c in low_corr:
            st.write(f"**{a}** ↔ **{b}**: {c:.2f}")


def render_maturity_calendar(positions: list[dict]) -> None:
    """Render fixed income maturity timeline."""
    rf_positions = [p for p in positions if p.get("asset_class") in ("TESOURO", "RENDA_FIXA_PRIVADA")]
    if not rf_positions:
        return

    st.subheader("📅 Vencimentos de Renda Fixa")

    rows = []
    for p in rf_positions:
        desc = p.get("descricao", p["ticker"])
        value = float(p.get("current_price", 0)) * float(p.get("quantity", 1))
        rentab = float(p.get("rentabilidade", 0)) * 100
        rows.append(
            {
                "Ativo": desc if desc != p["ticker"] else p["ticker"],
                "Classe": p["asset_class"],
                "Valor Atual": value,
                "Rentabilidade": rentab,
            }
        )

    import pandas as pd

    df = pd.DataFrame(rows).sort_values("Valor Atual", ascending=False)
    styled = df.style.format(
        {
            "Valor Atual": "R$ {:.2f}",
            "Rentabilidade": "{:.2f}%",
        }
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    total_rf = sum(r["Valor Atual"] for r in rows)
    st.info(f"Total em Renda Fixa: **R$ {total_rf:,.2f}** ({len(rows)} posições)")

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine.models import Asset


def compute_reserve_value(assets: list[Asset], positions: list[dict]) -> float:
    """Sum the current value of assets marked as emergency reserve."""
    reserve_tickers = {p["ticker"] for p in positions if p.get("is_reserve", False)}
    return sum(a.current_value for a in assets if a.ticker in reserve_tickers)


def render_emergency_reserve(
    assets: list[Asset],
    positions: list[dict],
    monthly_expenses: float,
    emergency_months: int,
) -> None:
    """Render the emergency reserve tracking tab."""
    st.subheader("🛡️ Reserva de Emergência")

    target_reserve = monthly_expenses * emergency_months
    current_reserve = compute_reserve_value(assets, positions)
    deficit = target_reserve - current_reserve
    coverage_months = current_reserve / monthly_expenses if monthly_expenses > 0 else 0
    pct_complete = (current_reserve / target_reserve * 100) if target_reserve > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Meta da Reserva", f"R$ {target_reserve:,.2f}")
    with col2:
        st.metric(
            "Reserva Atual",
            f"R$ {current_reserve:,.2f}",
            delta=f"{pct_complete:.0f}% da meta",
        )
    with col3:
        st.metric("Cobertura Atual", f"{coverage_months:.1f} meses")
    with col4:
        if deficit > 0:
            st.metric("Déficit", f"R$ {deficit:,.2f}", delta="Abaixo da meta", delta_color="inverse")
        else:
            st.metric("Superávit", f"R$ {abs(deficit):,.2f}", delta="Meta atingida!")

    st.divider()

    col_gauge, col_detail = st.columns([1, 1])

    with col_gauge:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=current_reserve,
                delta={"reference": target_reserve, "relative": False, "valueformat": ",.2f"},
                number={"prefix": "R$ ", "valueformat": ",.0f"},
                title={"text": "Reserva de Emergência"},
                gauge={
                    "axis": {"range": [0, target_reserve * 1.3], "tickformat": ",.0f"},
                    "bar": {"color": "#2ca02c" if pct_complete >= 100 else "#ff7f0e"},
                    "steps": [
                        {"range": [0, target_reserve * 0.5], "color": "#f8d7da"},
                        {"range": [target_reserve * 0.5, target_reserve], "color": "#fff3cd"},
                        {"range": [target_reserve, target_reserve * 1.3], "color": "#d4edda"},
                    ],
                    "threshold": {
                        "line": {"color": "#d62728", "width": 3},
                        "thickness": 0.8,
                        "value": target_reserve,
                    },
                },
            )
        )
        fig.update_layout(height=300, margin={"t": 50, "b": 10, "l": 30, "r": 30})
        st.plotly_chart(fig, use_container_width=True)

    with col_detail:
        st.markdown("**Composição da Reserva**")
        reserve_tickers = {p["ticker"] for p in positions if p.get("is_reserve", False)}
        reserve_assets = [a for a in assets if a.ticker in reserve_tickers]

        if reserve_assets:
            for a in sorted(reserve_assets, key=lambda x: -x.current_value):
                pct_of_reserve = (a.current_value / current_reserve * 100) if current_reserve > 0 else 0
                st.write(f"**{a.ticker}** — R$ {a.current_value:,.2f} ({pct_of_reserve:.1f}% da reserva)")
        else:
            st.info("Nenhum ativo marcado como reserva. Edite o portfólio e marque `is_reserve: true`.")

        if deficit > 0 and monthly_expenses > 0:
            st.divider()
            months_to_fill = deficit / monthly_expenses
            st.write(f"Ao ritmo de 1 despesa mensal por mês, faltam **{months_to_fill:.1f} meses** para completar.")


def render_capital_allocation(
    cash_injection: float,
    reserve_deficit: float,
) -> tuple[float, float]:
    """Render capital allocation split between reserve and investments.

    Returns (amount_to_reserve, amount_to_invest).
    """
    st.subheader("💰 Alocação do Capital")

    if reserve_deficit <= 0:
        st.success("Reserva de emergência completa! Todo o aporte vai para investimentos.")
        return 0.0, cash_injection

    st.warning(
        f"Reserva de emergência com déficit de **R$ {reserve_deficit:,.2f}**. "
        "Considere priorizar a reserva antes de investir."
    )

    reserve_pct = st.slider(
        "% do aporte para reserva de emergência",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        format="%d%%",
        key="reserve_split",
    )

    to_reserve = cash_injection * reserve_pct / 100.0
    to_invest = cash_injection - to_reserve

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aporte Total", f"R$ {cash_injection:,.2f}")
    with col2:
        st.metric("Para Reserva", f"R$ {to_reserve:,.2f}", delta=f"{reserve_pct}%")
    with col3:
        st.metric("Para Investimentos", f"R$ {to_invest:,.2f}", delta=f"{100 - reserve_pct}%")

    return to_reserve, to_invest

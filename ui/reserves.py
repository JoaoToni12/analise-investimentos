from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st


def get_reserve_value(meta: dict[str, Any]) -> float:
    """Get the current emergency reserve value from portfolio metadata."""
    reserve_data = meta.get("reserva_emergencia", {})
    return float(reserve_data.get("saldo", 0))


def render_emergency_reserve(
    meta: dict[str, Any],
    monthly_expenses: float,
    emergency_months: int,
) -> None:
    """Render the emergency reserve tracking tab."""
    st.subheader("🛡️ Reserva de Emergência")

    reserve_data = meta.get("reserva_emergencia", {})
    current_reserve = float(reserve_data.get("saldo", 0))
    local = reserve_data.get("local", "—")
    rendimento = reserve_data.get("rendimento", "—")

    target_reserve = monthly_expenses * emergency_months
    deficit = target_reserve - current_reserve
    coverage_months = current_reserve / monthly_expenses if monthly_expenses > 0 else 0
    pct_complete = (current_reserve / target_reserve * 100) if target_reserve > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Meta da Reserva", f"R$ {target_reserve:,.2f}")
    with col2:
        st.metric("Reserva Atual", f"R$ {current_reserve:,.2f}", delta=f"{pct_complete:.0f}% da meta")
    with col3:
        st.metric("Cobertura", f"{coverage_months:.1f} meses")
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
                    "axis": {"range": [0, max(target_reserve, current_reserve) * 1.2], "tickformat": ",.0f"},
                    "bar": {"color": "#2ca02c" if pct_complete >= 100 else "#ff7f0e"},
                    "steps": [
                        {"range": [0, target_reserve * 0.5], "color": "#f8d7da"},
                        {"range": [target_reserve * 0.5, target_reserve], "color": "#fff3cd"},
                        {"range": [target_reserve, max(target_reserve, current_reserve) * 1.2], "color": "#d4edda"},
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
        st.markdown("##### Onde está sua reserva")
        st.write(f"**Local:** {local}")
        st.write(f"**Rendimento:** {rendimento}")
        st.write(f"**Saldo:** R$ {current_reserve:,.2f}")

        st.divider()
        st.markdown("##### Por que separada?")
        st.caption(
            "A reserva de emergência deve ter **liquidez imediata** e **baixo risco**. "
            "Por isso fica fora dos investimentos de longo prazo (ações, FIIs, RF com carência). "
            "Contas remuneradas (PicPay, Nubank, etc.) ou Tesouro SELIC com resgate D+0 são ideais."
        )

        if deficit > 0 and monthly_expenses > 0:
            months_to_fill = deficit / monthly_expenses
            st.info(f"Faltam **{months_to_fill:.1f} meses** de despesa para completar a meta.")


def render_capital_allocation(
    cash_injection: float,
    reserve_deficit: float,
) -> tuple[float, float]:
    """Render capital allocation split between reserve and investments."""
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

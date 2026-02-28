from __future__ import annotations

import streamlit as st

from config import (
    DEFAULT_ABSOLUTE_BAND,
    DEFAULT_BLEND_FACTOR,
    DEFAULT_EMERGENCY_MONTHS,
    DEFAULT_MONTHLY_EXPENSES,
    DEFAULT_RELATIVE_BAND,
    DEFAULT_RISK_FREE_RATE,
)


def render_sidebar() -> dict:
    """Render the sidebar controls and return the user's parameter choices."""
    st.sidebar.header("Parâmetros")

    st.sidebar.subheader("💰 Capital para Investir")
    cash_injection = st.sidebar.number_input(
        "Aporte mensal (R$)",
        min_value=0.0,
        value=1000.0,
        step=100.0,
        format="%.2f",
    )

    st.sidebar.subheader("🛡️ Reserva de Emergência")
    monthly_expenses = st.sidebar.number_input(
        "Despesas mensais (R$)",
        min_value=0.0,
        value=DEFAULT_MONTHLY_EXPENSES,
        step=500.0,
        format="%.2f",
    )
    emergency_months = st.sidebar.number_input(
        "Meses de cobertura",
        min_value=1,
        max_value=24,
        value=DEFAULT_EMERGENCY_MONTHS,
        step=1,
    )

    st.sidebar.subheader("📊 Markowitz")
    risk_free_rate = st.sidebar.number_input(
        "Taxa livre de risco (SELIC)",
        min_value=0.0,
        max_value=1.0,
        value=DEFAULT_RISK_FREE_RATE,
        step=0.0025,
        format="%.4f",
    )
    blend_factor = st.sidebar.slider(
        "Fator de blend Markowitz",
        min_value=0.0,
        max_value=1.0,
        value=DEFAULT_BLEND_FACTOR,
        step=0.05,
        help="0 = manter pesos atuais | 1 = 100% Markowitz",
    )

    st.sidebar.subheader("🎯 Bandas de Tolerância")
    relative_band = st.sidebar.slider(
        "Banda relativa",
        min_value=0.0,
        max_value=0.50,
        value=DEFAULT_RELATIVE_BAND,
        step=0.05,
        format="%.0%%",
        help="Desvio proporcional ao peso alvo (ex: 20% de 5% = ±1pp)",
    )
    absolute_band = st.sidebar.slider(
        "Banda absoluta (pp)",
        min_value=0.0,
        max_value=5.0,
        value=DEFAULT_ABSOLUTE_BAND,
        step=0.25,
        format="%.2f",
        help="Desvio fixo em pontos percentuais (ex: 1.5 = ±1.5pp)",
    )

    st.sidebar.divider()
    refresh = st.sidebar.button("🔄 Atualizar Cotações", use_container_width=True)

    return {
        "cash_injection": cash_injection,
        "monthly_expenses": monthly_expenses,
        "emergency_months": emergency_months,
        "risk_free_rate": risk_free_rate,
        "blend_factor": blend_factor,
        "relative_band": relative_band,
        "absolute_band": absolute_band,
        "refresh": refresh,
    }

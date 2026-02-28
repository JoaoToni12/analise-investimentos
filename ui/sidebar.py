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
    """Render sidebar with primary controls visible and advanced settings collapsed."""
    st.sidebar.header("Parâmetros")

    st.sidebar.subheader("💰 APORTE")
    cash_injection = st.sidebar.number_input(
        "Valor mensal (R$)", min_value=0.0, value=1000.0, step=100.0, format="%.2f"
    )

    st.sidebar.subheader("🛡️ RESERVA")
    monthly_expenses = st.sidebar.number_input(
        "Despesas mensais (R$)", min_value=0.0, value=DEFAULT_MONTHLY_EXPENSES, step=500.0, format="%.2f"
    )
    emergency_months = st.sidebar.number_input(
        "Meses de cobertura", min_value=1, max_value=24, value=DEFAULT_EMERGENCY_MONTHS, step=1
    )

    with st.sidebar.expander("⚙️ Configurações Avançadas"):
        st.caption("MARKOWITZ")
        risk_free_rate = st.number_input(
            "Taxa livre de risco (SELIC)",
            min_value=0.0,
            max_value=1.0,
            value=DEFAULT_RISK_FREE_RATE,
            step=0.0025,
            format="%.4f",
        )
        blend_factor = st.slider(
            "Blend Markowitz",
            min_value=0.0,
            max_value=1.0,
            value=DEFAULT_BLEND_FACTOR,
            step=0.05,
            help="0 = pesos manuais | 1 = 100% otimização",
        )
        st.caption("BANDAS DE TOLERÂNCIA")
        relative_band_pct = st.slider(
            "Banda relativa (%)",
            min_value=0,
            max_value=50,
            value=int(DEFAULT_RELATIVE_BAND * 100),
            step=5,
            format="%d%%",
            help="Desvio proporcional ao peso alvo",
        )
        absolute_band = st.slider(
            "Banda absoluta (pp)",
            min_value=0.0,
            max_value=5.0,
            value=DEFAULT_ABSOLUTE_BAND,
            step=0.25,
            format="%.2f pp",
            help="Desvio fixo em pontos percentuais",
        )

    st.sidebar.divider()
    refresh = st.sidebar.button("🔄 Atualizar Cotações", use_container_width=True, type="primary")

    return {
        "cash_injection": cash_injection,
        "monthly_expenses": monthly_expenses,
        "emergency_months": emergency_months,
        "risk_free_rate": risk_free_rate,
        "blend_factor": blend_factor,
        "relative_band": relative_band_pct / 100.0,
        "absolute_band": absolute_band,
        "refresh": refresh,
    }

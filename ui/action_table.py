from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.models import Asset, Band, Order, ZoneStatus


def render_action_table(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
    orders: list[Order],
    residual_cash: float,
) -> None:
    """Render the deterministic action table with buy/sell recommendations."""
    st.subheader("Tabela de Ação de Execução")

    order_map: dict[str, Order] = {o.ticker: o for o in orders}

    rows = []
    for a in assets:
        status, _band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        order = order_map.get(a.ticker)

        rows.append(
            {
                "Ticker": a.ticker,
                "Classe": a.asset_class.value,
                "Preço Atual": a.current_price,
                "Peso Atual (%)": round(a.current_weight, 2),
                "Alvo (%)": round(a.target_weight, 2),
                "Status": status.value,
                "Ação": order.action.value if order else "—",
                "Qtd Sugerida": order.quantity if order else 0,
                "Valor Estimado (R$)": round(order.amount, 2) if order else 0.0,
            }
        )

    df = pd.DataFrame(rows)

    def _color_status(val: str) -> str:
        if val == "BUY":
            return "background-color: #d4edda; color: #155724"
        if val == "SELL":
            return "background-color: #f8d7da; color: #721c24"
        return "background-color: #e2e3e5; color: #383d41"

    styled = df.style.applymap(_color_status, subset=["Status", "Ação"])
    styled = styled.format(
        {
            "Preço Atual": "R$ {:.2f}",
            "Peso Atual (%)": "{:.2f}%",
            "Alvo (%)": "{:.2f}%",
            "Valor Estimado (R$)": "R$ {:.2f}",
        }
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.info(f"💰 Caixa remanescente após alocação: **R$ {residual_cash:,.2f}**")

    col1, _ = st.columns([1, 3])
    with col1:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar para CSV",
            data=csv_data,
            file_name="ordens_rebalanceamento.csv",
            mime="text/csv",
        )

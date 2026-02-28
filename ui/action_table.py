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
    for a in sorted(assets, key=lambda x: -x.current_value):
        status, band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        order = order_map.get(a.ticker)
        band_str = f"[{band.lower_bound:.1f}%, {band.upper_bound:.1f}%]" if band else "—"

        rows.append(
            {
                "Ticker": a.ticker,
                "Classe": a.asset_class.value,
                "Preço": a.current_price,
                "Valor (R$)": round(a.current_value, 2),
                "Peso Atual": round(a.current_weight, 2),
                "Alvo": round(a.target_weight, 2),
                "Banda": band_str,
                "Status": status.value,
                "Ação": order.action.value if order else "—",
                "Qtd": order.quantity if order else 0,
                "Custo (R$)": round(order.amount, 2) if order else 0.0,
            }
        )

    df = pd.DataFrame(rows)

    def _color_status(val: str) -> str:
        if val == "BUY":
            return "background-color: #d4edda; color: #155724"
        if val == "SELL":
            return "background-color: #f8d7da; color: #721c24"
        return "background-color: #f0f0f0; color: #383d41"

    styled = df.style.map(_color_status, subset=["Status", "Ação"])
    styled = styled.format(
        {
            "Preço": "R$ {:.2f}",
            "Valor (R$)": "R$ {:.2f}",
            "Peso Atual": "{:.2f}%",
            "Alvo": "{:.2f}%",
            "Custo (R$)": "R$ {:.2f}",
        }
    )

    st.dataframe(styled, use_container_width=True, hide_index=True, height=min(600, 35 * len(rows) + 40))

    total_buy = sum(o.amount for o in orders if o.action.value == "BUY")
    total_sell = sum(o.amount for o in orders if o.action.value == "SELL")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Compras", f"R$ {total_buy:,.2f}")
    with col2:
        st.metric("Total Vendas", f"R$ {total_sell:,.2f}")
    with col3:
        st.metric("Caixa Remanescente", f"R$ {residual_cash:,.2f}")

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exportar Ordens (CSV)",
        data=csv_data,
        file_name="ordens_rebalanceamento.csv",
        mime="text/csv",
    )

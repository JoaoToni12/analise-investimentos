from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.models import Asset, Band, Order, ZoneStatus
from ui.theme import COLORS


def render_action_table(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
    orders: list[Order],
    residual_cash: float,
) -> None:
    """Two-tier action table: quick action cards + expandable detail."""
    st.subheader("📋 Ordens de Execução")

    order_map: dict[str, Order] = {o.ticker: o for o in orders}

    # Tier 1: Action cards for actionable items
    actionable = [o for o in orders if o.quantity > 0]
    if actionable:
        st.markdown("##### Ações Necessárias")
        cols = st.columns(min(len(actionable), 4))
        for i, order in enumerate(actionable):
            asset = next((a for a in assets if a.ticker == order.ticker), None)
            if not asset:
                continue
            col = cols[i % min(len(actionable), 4)]
            color = COLORS["success"] if order.action.value == "BUY" else COLORS["danger"]
            label = "COMPRAR" if order.action.value == "BUY" else "VENDER"
            with col:
                st.markdown(
                    f"""<div style="border-left:4px solid {color};background:#1A1D23;
                    border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:6px;">
                    <div style="font-weight:700;color:{color};font-size:0.7rem;">{label}</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#FAFAFA;">{order.ticker}</div>
                    <div style="color:#8B8D97;font-size:0.8rem;">
                        {order.quantity} un × R$ {asset.current_price:,.2f}</div>
                    <div style="font-weight:600;color:#FAFAFA;margin-top:4px;">
                        R$ {order.amount:,.2f}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.success("Carteira equilibrada — nenhuma ordem necessária com o aporte atual.")

    # Summary metrics
    total_buy = sum(o.amount for o in orders if o.action.value == "BUY")
    total_sell = sum(o.amount for o in orders if o.action.value == "SELL")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Compras", f"R$ {total_buy:,.2f}")
    with col2:
        st.metric("Total Vendas", f"R$ {total_sell:,.2f}")
    with col3:
        st.metric("Caixa Remanescente", f"R$ {residual_cash:,.2f}")

    # Tier 2: Full detail table (collapsed by default)
    with st.expander("📊 Tabela Completa de Posições", expanded=False):
        rows = []
        for a in sorted(assets, key=lambda x: -x.current_value):
            status, band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
            order = order_map.get(a.ticker)
            rows.append(
                {
                    "Ticker": a.ticker,
                    "Classe": a.asset_class.value,
                    "Preço": a.current_price,
                    "Valor": round(a.current_value, 2),
                    "Peso": round(a.current_weight, 2),
                    "Alvo": round(a.target_weight, 2),
                    "Status": status.value,
                    "Ação": order.action.value if order else "—",
                    "Qtd": order.quantity if order else 0,
                    "Custo": round(order.amount, 2) if order else 0.0,
                }
            )

        df = pd.DataFrame(rows)

        def _color_status(val: str) -> str:
            if val == "BUY":
                return "background-color: #0D2818; color: #22C55E"
            if val == "SELL":
                return "background-color: #1C0F12; color: #EF4444"
            return "color: #6B7280"

        styled = df.style.map(_color_status, subset=["Status", "Ação"])
        styled = styled.format(
            {
                "Preço": "R$ {:.2f}",
                "Valor": "R$ {:.2f}",
                "Peso": "{:.2f}%",
                "Alvo": "{:.2f}%",
                "Custo": "R$ {:.2f}",
            }
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=min(600, 35 * len(rows) + 40))

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar Ordens (CSV)", data=csv_data, file_name="ordens_rebalanceamento.csv", mime="text/csv"
        )

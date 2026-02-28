from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from engine.models import Asset, AssetClass, Band, Order, OrderAction, ZoneStatus
from engine.portfolio import compute_class_weights, compute_gaps, compute_portfolio_value
from engine.rebalancer import compute_class_targets
from ui.theme import CLASS_LABELS, kpi_card, signal_strip


def render_dashboard(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
    meta: dict[str, Any] | None = None,
    orders: list[Order] | None = None,
) -> None:
    """Render professional dashboard with KPI cards, signals, and class table."""
    meta = meta or {}
    orders = orders or []
    total_value = compute_portfolio_value(assets)
    total_cost = sum(a.cost_basis for a in assets)
    dividends = float(meta.get("dividendos_recebidos", 0))
    total_pnl = (total_value - total_cost) + dividends
    pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Patrimônio Total", f"R$ {total_value:,.2f}", f"{pnl_pct:+.1f}%", pnl_pct >= 0, "📊")
    with col2:
        cap_gain = total_value - total_cost
        kpi_card("Ganho de Capital", f"R$ {cap_gain:,.2f}", positive=cap_gain >= 0, icon="📈")
    with col3:
        kpi_card("Proventos", f"R$ {dividends:,.2f}", icon="💰")
    with col4:
        kpi_card("Lucro Total", f"R$ {total_pnl:,.2f}", f"{pnl_pct:+.1f}%", total_pnl >= 0, "🏆")

    st.write("")

    # Signal strip based on ACTUAL orders, not just zone status
    n_buy = sum(1 for o in orders if o.action == OrderAction.BUY)
    n_sell = sum(1 for o in orders if o.action == OrderAction.SELL)
    n_hold = len(assets) - n_buy - n_sell
    signal_strip(n_buy, n_hold, n_sell)

    col_classes, col_gaps = st.columns([3, 2])

    with col_classes:
        st.markdown("##### Alocação por Classe")
        class_w = compute_class_weights(assets)
        class_t = compute_class_targets(assets)

        rows = []
        for cls in AssetClass:
            current = class_w.get(cls, 0)
            target = class_t.get(cls, 0)
            if current == 0 and target == 0:
                continue
            gap = current - target
            status = "✅" if abs(gap) < 2 else ("⚠️" if abs(gap) < 5 else "🚨")
            rows.append(
                {
                    "Classe": CLASS_LABELS.get(cls.value, cls.value),
                    "Atual": current,
                    "Alvo": target,
                    "Gap": gap,
                    " ": status,
                }
            )

        if rows:
            df = pd.DataFrame(rows)

            def _gap_color(val: float) -> str:
                if abs(val) < 2:
                    return "color: #22C55E"
                if abs(val) < 5:
                    return "color: #F59E0B"
                return "color: #EF4444; font-weight: bold"

            styled = df.style.map(_gap_color, subset=["Gap"])
            styled = styled.format({"Atual": "{:.1f}%", "Alvo": "{:.1f}%", "Gap": "{:+.1f}pp"})
            st.dataframe(styled, use_container_width=True, hide_index=True, height=min(300, len(rows) * 40 + 40))

    with col_gaps:
        st.markdown("##### Top Gaps Individuais")
        gaps = compute_gaps(assets)
        sorted_gaps = sorted(gaps.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for ticker, gap in sorted_gaps:
            status = zones.get(ticker, (ZoneStatus.HOLD, None))[0]
            icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(status.value, "⚪")
            st.write(f"{icon} **{ticker}** {gap:+.2f}pp ({status.value})")

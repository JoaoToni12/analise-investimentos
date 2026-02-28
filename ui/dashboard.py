from __future__ import annotations

import streamlit as st

from engine.models import Asset, AssetClass, Band, ZoneStatus
from engine.portfolio import compute_class_weights, compute_gaps, compute_portfolio_value


def render_dashboard(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> None:
    """Render top-level KPIs and status indicators."""
    total_value = compute_portfolio_value(assets)
    total_pnl = sum(a.pnl for a in assets)
    pnl_pct = (total_pnl / (total_value - total_pnl) * 100) if total_value > total_pnl and total_value > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patrimônio Total", f"R$ {total_value:,.2f}")
    with col2:
        st.metric("Rentabilidade", f"R$ {total_pnl:,.2f}", delta=f"{pnl_pct:+.1f}%")
    with col3:
        st.metric("Ativos na Carteira", str(len(assets)))
    with col4:
        urgent = sum(1 for _, (s, _) in zones.items() if s == ZoneStatus.SELL)
        st.metric("Distorções Urgentes", str(urgent), delta="SELL" if urgent > 0 else "OK", delta_color="inverse")

    st.divider()

    col_gaps, col_classes = st.columns(2)

    with col_gaps:
        st.subheader("Maiores Gaps")
        gaps = compute_gaps(assets)
        sorted_gaps = sorted(gaps.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for ticker, gap in sorted_gaps:
            status_icon = "🟢" if abs(gap) < 2 else ("🔴" if gap < -2 else "🟡")
            st.write(f"{status_icon} **{ticker}**: {gap:+.2f} pp")

    with col_classes:
        st.subheader("Peso por Classe de Ativo")
        class_w = compute_class_weights(assets)
        for cls in AssetClass:
            weight = class_w.get(cls, 0)
            if weight > 0:
                st.write(f"**{cls.value}**: {weight:.1f}%")

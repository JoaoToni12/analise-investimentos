from __future__ import annotations

from typing import Any

import streamlit as st

from engine.models import Asset, AssetClass, Band, ZoneStatus
from engine.portfolio import compute_class_weights, compute_gaps, compute_portfolio_value
from engine.rebalancer import compute_class_targets

CLASS_LABELS = {
    AssetClass.ACAO: "Ações",
    AssetClass.FII: "FIIs",
    AssetClass.ETF: "ETFs",
    AssetClass.BDR: "BDRs",
    AssetClass.CRYPTO: "Crypto",
    AssetClass.TESOURO: "Tesouro Direto",
    AssetClass.RENDA_FIXA_PRIVADA: "Renda Fixa",
}


def render_dashboard(
    assets: list[Asset],
    zones: dict[str, tuple[ZoneStatus, Band]],
    meta: dict[str, Any] | None = None,
) -> None:
    """Render top-level KPIs, dividends and class-level status."""
    meta = meta or {}
    total_value = compute_portfolio_value(assets)
    total_cost = sum(a.cost_basis for a in assets)
    dividends = float(meta.get("dividendos_recebidos", 0))
    total_pnl = (total_value - total_cost) + dividends
    pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # --- Row 1: Main KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patrimônio Total", f"R$ {total_value:,.2f}", delta=f"{pnl_pct:+.1f}%")
    with col2:
        cap_gain = total_value - total_cost
        st.metric("Ganho de Capital", f"R$ {cap_gain:,.2f}")
    with col3:
        st.metric("Proventos Recebidos", f"R$ {dividends:,.2f}")
    with col4:
        st.metric("Lucro Total", f"R$ {total_pnl:,.2f}")

    # --- Row 2: Alerts ---
    n_buy = sum(1 for _, (s, _) in zones.items() if s == ZoneStatus.BUY)
    n_sell = sum(1 for _, (s, _) in zones.items() if s == ZoneStatus.SELL)
    n_hold = len(zones) - n_buy - n_sell

    alert_cols = st.columns(4)
    with alert_cols[0]:
        st.metric("Ativos", f"{len(assets)} posições")
    with alert_cols[1]:
        st.metric("BUY", str(n_buy), delta="comprar" if n_buy > 0 else None)
    with alert_cols[2]:
        st.metric("HOLD", str(n_hold))
    with alert_cols[3]:
        st.metric("SELL", str(n_sell), delta="vender" if n_sell > 0 else None, delta_color="inverse")

    st.divider()

    # --- Class-level allocation table ---
    col_classes, col_gaps = st.columns([3, 2])

    with col_classes:
        st.markdown("##### Alocação por Classe")
        class_w = compute_class_weights(assets)
        class_t = compute_class_targets(assets)

        header = st.columns([2, 1, 1, 1])
        header[0].markdown("**Classe**")
        header[1].markdown("**Atual**")
        header[2].markdown("**Alvo**")
        header[3].markdown("**Gap**")

        for cls in AssetClass:
            current = class_w.get(cls, 0)
            target = class_t.get(cls, 0)
            if current == 0 and target == 0:
                continue
            gap = current - target
            icon = "🟢" if abs(gap) < 2 else ("🔴" if gap < -2 else "🟡")
            row = st.columns([2, 1, 1, 1])
            row[0].write(f"{icon} {CLASS_LABELS.get(cls, cls.value)}")
            row[1].write(f"{current:.1f}%")
            row[2].write(f"{target:.1f}%")
            row[3].write(f"{gap:+.1f}pp")

    with col_gaps:
        st.markdown("##### Top 5 Gaps Individuais")
        gaps = compute_gaps(assets)
        sorted_gaps = sorted(gaps.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for ticker, gap in sorted_gaps:
            status = zones.get(ticker, (ZoneStatus.HOLD, None))[0]
            color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(status.value, "⚪")
            st.write(f"{color} **{ticker}** {gap:+.2f}pp ({status.value})")

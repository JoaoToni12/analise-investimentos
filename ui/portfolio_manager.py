from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from engine.models import AssetClass
from ingestion.portfolio_loader import import_csv, load_portfolio, save_portfolio


def render_portfolio_manager() -> list[dict[str, Any]]:
    """Render the portfolio management UI and return the current positions."""
    st.subheader("Gestão da Carteira")

    tab_edit, tab_import = st.tabs(["Editar Posições", "Importar CSV"])

    positions = load_portfolio()

    with tab_edit:
        positions = _render_editor(positions)

    with tab_import:
        positions = _render_csv_import(positions)

    return positions


def _render_editor(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Editable table for portfolio positions."""
    class_options = [c.value for c in AssetClass]

    if positions:
        df = pd.DataFrame(positions)
        for col in ["ticker", "asset_class", "quantity", "avg_price", "target_weight_pct"]:
            if col not in df.columns:
                df[col] = "" if col in ("ticker", "asset_class") else 0.0
    else:
        df = pd.DataFrame(columns=["ticker", "asset_class", "quantity", "avg_price", "target_weight_pct"])

    edited_df = st.data_editor(
        df,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True),
            "asset_class": st.column_config.SelectboxColumn("Classe", options=class_options, required=True),
            "quantity": st.column_config.NumberColumn("Quantidade", min_value=0, format="%.2f"),
            "avg_price": st.column_config.NumberColumn("Preço Médio (R$)", min_value=0, format="%.2f"),
            "target_weight_pct": st.column_config.NumberColumn(
                "Peso Alvo (%)", min_value=0, max_value=100, format="%.2f"
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_editor",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar Alterações", use_container_width=True):
            new_positions = edited_df.to_dict("records")
            new_positions = [p for p in new_positions if p.get("ticker")]
            for p in new_positions:
                p["ticker"] = str(p["ticker"]).strip().upper()
                p["asset_class"] = str(p.get("asset_class", "ACAO")).strip().upper()
            try:
                save_portfolio(new_positions)
                st.success(f"{len(new_positions)} posições salvas com sucesso.")
                positions = new_positions
            except ValueError as e:
                st.error(f"Erro de validação: {e}")

    with col2:
        total_weight = sum(p.get("target_weight_pct", 0) for p in positions)
        st.metric("Soma dos pesos alvo", f"{total_weight:.1f}%")

    return positions


def _render_csv_import(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CSV file uploader with preview."""
    uploaded = st.file_uploader(
        "Arraste ou selecione um CSV/Excel da corretora",
        type=["csv", "xlsx", "xls"],
        key="csv_uploader",
    )
    if uploaded is not None:
        try:
            imported = import_csv(uploaded)
            st.dataframe(pd.DataFrame(imported), use_container_width=True)

            if st.button("✅ Confirmar Importação", use_container_width=True):
                save_portfolio(imported)
                st.success(f"{len(imported)} posições importadas com sucesso.")
                positions = imported
        except ValueError as e:
            st.error(f"Erro na importação: {e}")

    return positions

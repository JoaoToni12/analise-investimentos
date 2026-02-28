from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from config import PORTFOLIO_PATH

REQUIRED_FIELDS = {"ticker", "asset_class", "quantity", "avg_price", "target_weight_pct"}
OPTIONAL_FIELDS = {"current_price", "is_reserve", "currency", "usd_avg_price", "usd_current_price", "rentabilidade"}

COLUMN_ALIASES: dict[str, list[str]] = {
    "ticker": [
        "ticker",
        "codigo",
        "ativo",
        "symbol",
        "code",
        "código",
        "papel",
        "cod",
        "cod.",
        "produto",  # Clear, XP, Rico, NuInvest
    ],
    "asset_class": [
        "asset_class",
        "classe",
        "class",
        "tipo",
        "type",
        "categoria",
        "segmento",
        "mercado",
        "tipo ativo",
    ],
    "quantity": [
        "quantity",
        "quantidade",
        "qtd",
        "qty",
        "shares",
        "qtde",
        "qtde.",
        "quantidade disponível",
        "quant",
    ],
    "avg_price": [
        "avg_price",
        "preco_medio",
        "pm",
        "average_price",
        "cost",
        "preço médio",
        "preco medio",
        "valor medio",
        "custo médio",
        "preço de compra",
        "preco compra",
    ],
    "target_weight_pct": [
        "target_weight_pct",
        "target",
        "peso_alvo",
        "target_weight",
        "alvo",
        "peso alvo",
        "meta",
        "% alvo",
        "alocação alvo",
    ],
}


def _resolve_column(df_columns: list[str], field: str) -> str | None:
    """Find matching column name from known aliases."""
    aliases = COLUMN_ALIASES.get(field, [field])
    lower_cols = {c.lower().strip(): c for c in df_columns}
    for alias in aliases:
        if alias.lower() in lower_cols:
            return lower_cols[alias.lower()]
    return None


def load_portfolio(path: Path | None = None) -> list[dict[str, Any]]:
    """Load portfolio positions from JSON file."""
    path = path or PORTFOLIO_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_portfolio(positions: list[dict[str, Any]], path: Path | None = None) -> None:
    """Persist portfolio positions to JSON file after validation."""
    validate_portfolio(positions)
    path = path or PORTFOLIO_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)


def import_csv(file) -> list[dict[str, Any]]:
    """Parse a CSV/Excel file from a broker into the standard portfolio schema.

    Accepts a file path, file-like object, or Streamlit UploadedFile.
    Column matching is flexible via COLUMN_ALIASES.
    """
    if isinstance(file, (str, Path)):
        path = Path(file)
        if path.suffix in (".xls", ".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file, sep=None, engine="python")
    else:
        df = pd.read_csv(file, sep=None, engine="python")

    col_map: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        resolved = _resolve_column(list(df.columns), field)
        if resolved is None:
            raise ValueError(f"Coluna obrigatória '{field}' não encontrada. Colunas disponíveis: {list(df.columns)}")
        col_map[field] = resolved

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        records.append(
            {
                "ticker": str(row[col_map["ticker"]]).strip().upper(),
                "asset_class": str(row[col_map["asset_class"]]).strip().upper(),
                "quantity": float(row[col_map["quantity"]]),
                "avg_price": float(row[col_map["avg_price"]]),
                "target_weight_pct": float(row[col_map["target_weight_pct"]]),
            }
        )

    validate_portfolio(records)
    return records


def validate_portfolio(positions: list[dict[str, Any]]) -> None:
    """Validate portfolio data integrity."""
    if not positions:
        return

    tickers_seen: set[str] = set()
    for pos in positions:
        missing = REQUIRED_FIELDS - set(pos.keys())
        if missing:
            raise ValueError(f"Campos faltando em posição: {missing}")

        ticker = pos["ticker"]
        if ticker in tickers_seen:
            raise ValueError(f"Ticker duplicado: {ticker}")
        tickers_seen.add(ticker)

        if pos["quantity"] < 0:
            raise ValueError(f"Quantidade negativa para {ticker}: {pos['quantity']}")
        if pos["avg_price"] < 0:
            raise ValueError(f"Preço médio negativo para {ticker}: {pos['avg_price']}")
        if not 0 <= pos["target_weight_pct"] <= 100:
            raise ValueError(f"Peso alvo fora de [0, 100] para {ticker}: {pos['target_weight_pct']}")

    total_weight = sum(p["target_weight_pct"] for p in positions)
    if total_weight > 100.01:
        raise ValueError(f"Soma dos pesos alvo excede 100%: {total_weight:.2f}%")

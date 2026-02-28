from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BRAPI_TOKEN: str = os.getenv("BRAPI_TOKEN", "")
BRAPI_BASE_URL: str = "https://brapi.dev/api"

PORTFOLIO_PATH: Path = BASE_DIR / "data" / "portfolio.json"
PORTFOLIO_META_PATH: Path = BASE_DIR / "data" / "portfolio_meta.json"

DEFAULT_LOOKBACK: str = "2y"
TRADING_DAYS_PER_YEAR: int = 252

DEFAULT_RISK_FREE_RATE: float = 0.15  # SELIC (atualizada fev/2026)
DEFAULT_RELATIVE_BAND: float = 0.20  # 20% of target weight
DEFAULT_ABSOLUTE_BAND: float = 1.5  # 1.5 percentage points
DEFAULT_BLEND_FACTOR: float = 0.30  # 30% Markowitz

DEFAULT_MAX_ORDERS: int = 5
DEFAULT_MONTHLY_EXPENSES: float = 3000.0
DEFAULT_EMERGENCY_MONTHS: int = 6

# Tickers that brapi.dev cannot price (manual/fallback pricing)
NON_BRAPI_PREFIXES = ("TESOURO_", "USDT", "ALAB", "CDB_", "CRI_", "LCA_", "LCI_")

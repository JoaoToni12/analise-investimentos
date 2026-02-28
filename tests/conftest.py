from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.models import Asset, AssetClass

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_portfolio_data() -> list[dict]:
    with open(FIXTURES_DIR / "sample_portfolio.json") as f:
        return json.load(f)


@pytest.fixture
def sample_quotes() -> dict[str, float]:
    with open(FIXTURES_DIR / "sample_quotes.json") as f:
        return json.load(f)


@pytest.fixture
def sample_assets(sample_portfolio_data, sample_quotes) -> list[Asset]:
    """Build Asset objects with deterministic current prices."""
    assets = []
    for p in sample_portfolio_data:
        ticker = p["ticker"]
        assets.append(
            Asset(
                ticker=ticker,
                asset_class=AssetClass.from_str(p["asset_class"]),
                quantity=p["quantity"],
                avg_price=p["avg_price"],
                current_price=sample_quotes.get(ticker, p["avg_price"]),
                target_weight=p["target_weight_pct"],
            )
        )
    return assets


@pytest.fixture
def sample_prices_df() -> pd.DataFrame:
    """Deterministic historical prices for 5 assets over 252 days."""
    rng = np.random.default_rng(42)
    n_days = 252
    tickers = ["PETR4", "VALE3", "ITUB4", "WEGE3", "BBAS3"]

    base_prices = [30.0, 70.0, 26.0, 36.0, 43.0]
    data = {}
    for ticker, base in zip(tickers, base_prices):
        daily_returns = rng.normal(0.0005, 0.02, n_days)
        prices = base * np.cumprod(1 + daily_returns)
        data[ticker] = prices

    dates = pd.bdate_range(end="2026-02-27", periods=n_days)
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def tmp_portfolio_file(tmp_path) -> Path:
    return tmp_path / "test_portfolio.json"

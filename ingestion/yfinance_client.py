from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from config import DEFAULT_LOOKBACK

logger = logging.getLogger(__name__)

B3_SUFFIX = ".SA"
CRYPTO_SUFFIX = "-USD"

ASSET_CLASSES_B3 = {"ACAO", "FII", "ETF", "BDR"}
ASSET_CLASSES_CRYPTO = {"CRYPTO"}


def to_yfinance_ticker(ticker: str, asset_class: str = "ACAO") -> str:
    """Convert local ticker to yfinance format.

    PETR4 (ACAO) -> PETR4.SA
    BTC (CRYPTO) -> BTC-USD
    """
    upper_class = asset_class.upper()
    upper_ticker = ticker.upper()
    if upper_class in ASSET_CLASSES_CRYPTO:
        if not upper_ticker.endswith(CRYPTO_SUFFIX):
            return f"{upper_ticker}{CRYPTO_SUFFIX}"
        return upper_ticker
    if upper_class in ASSET_CLASSES_B3:
        if not upper_ticker.endswith(B3_SUFFIX):
            return f"{upper_ticker}{B3_SUFFIX}"
        return upper_ticker
    return upper_ticker


def get_historical_prices(
    tickers: list[str],
    asset_classes: list[str] | None = None,
    period: str | None = None,
) -> pd.DataFrame:
    """Download adjusted close prices for all tickers via yfinance.

    Returns a DataFrame indexed by date with original tickers as columns.
    """
    period = period or DEFAULT_LOOKBACK
    if asset_classes is None:
        asset_classes = ["ACAO"] * len(tickers)

    yf_tickers = [to_yfinance_ticker(t, ac) for t, ac in zip(tickers, asset_classes)]
    ticker_map = dict(zip(yf_tickers, tickers))

    if not yf_tickers:
        return pd.DataFrame()

    try:
        raw = yf.download(yf_tickers, period=period, auto_adjust=True, progress=False)
    except Exception as exc:
        logger.error("yfinance download error: %s", exc)
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].copy()
        prices.columns = [yf_tickers[0]] if len(yf_tickers) == 1 else prices.columns

    prices = prices.rename(columns=ticker_map)
    prices = prices.dropna(how="all")
    return prices

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

SPECIAL_YF_TICKERS: dict[str, str] = {
    "USDT": "USDT-BRL",
    "ALAB": "ALAB",
}


def to_yfinance_ticker(ticker: str, asset_class: str = "ACAO") -> str:
    """Convert local ticker to yfinance format."""
    upper_ticker = ticker.upper()
    upper_class = asset_class.upper()

    if upper_ticker in SPECIAL_YF_TICKERS:
        return SPECIAL_YF_TICKERS[upper_ticker]

    if upper_class in ASSET_CLASSES_CRYPTO:
        if not upper_ticker.endswith(CRYPTO_SUFFIX):
            return f"{upper_ticker}{CRYPTO_SUFFIX}"
        return upper_ticker
    if upper_class in ASSET_CLASSES_B3:
        if not upper_ticker.endswith(B3_SUFFIX):
            return f"{upper_ticker}{B3_SUFFIX}"
        return upper_ticker
    return upper_ticker


def get_yfinance_quotes(tickers: list[str], asset_classes: list[str] | None = None) -> dict[str, float]:
    """Fetch current prices for tickers via yfinance (for non-brapi assets)."""
    if asset_classes is None:
        asset_classes = ["CRYPTO"] * len(tickers)

    results: dict[str, float] = {}
    for ticker, cls in zip(tickers, asset_classes):
        yf_ticker = to_yfinance_ticker(ticker, cls)
        try:
            info = yf.Ticker(yf_ticker)
            hist = info.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if ticker == "ALAB":
                    price = _convert_usd_to_brl(price)
                results[ticker] = price
        except Exception as exc:
            logger.warning("yfinance quote failed for %s (%s): %s", ticker, yf_ticker, exc)

    return results


def _convert_usd_to_brl(usd_amount: float) -> float:
    """Convert USD to BRL using yfinance exchange rate."""
    try:
        fx = yf.Ticker("BRL=X")
        hist = fx.history(period="1d")
        if not hist.empty:
            rate = float(hist["Close"].iloc[-1])
            return usd_amount * rate
    except Exception:
        pass
    return usd_amount * 5.80  # fallback rate


def get_historical_prices(
    tickers: list[str],
    asset_classes: list[str] | None = None,
    period: str | None = None,
) -> pd.DataFrame:
    """Download adjusted close prices for all tickers via yfinance."""
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

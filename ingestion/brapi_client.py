from __future__ import annotations

import logging
import time

import requests

from config import BRAPI_BASE_URL, BRAPI_TOKEN

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 20
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0


def get_batch_quotes(tickers: list[str], token: str | None = None) -> dict[str, float]:
    """Fetch real-time quotes for multiple tickers in a single batch request.

    Returns a dict mapping ticker -> regularMarketPrice.
    Tickers that fail to resolve are silently omitted.
    """
    token = token or BRAPI_TOKEN
    if not token:
        logger.warning("BRAPI_TOKEN não configurado — cotações indisponíveis")
        return {}

    results: dict[str, float] = {}

    for i in range(0, len(tickers), MAX_BATCH_SIZE):
        batch = tickers[i : i + MAX_BATCH_SIZE]
        joined = ",".join(batch)
        url = f"{BRAPI_BASE_URL}/quote/{joined}"
        params = {"token": token}

        data = _request_with_retry(url, params)
        if data is None:
            continue

        for item in data.get("results", []):
            symbol = item.get("symbol", "")
            price = item.get("regularMarketPrice")
            if symbol and price is not None:
                results[symbol] = float(price)

    return results


def _request_with_retry(url: str, params: dict, retries: int = MAX_RETRIES) -> dict | None:
    """GET request with exponential backoff on rate-limit / transient errors."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = BACKOFF_FACTOR ** (attempt + 1)
                logger.warning("Rate limit (429) — aguardando %.1fs", wait)
                time.sleep(wait)
                continue
            logger.error("brapi HTTP %d: %s", resp.status_code, resp.text[:200])
            return None
        except requests.RequestException as exc:
            logger.error("brapi request error (tentativa %d): %s", attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(BACKOFF_FACTOR ** (attempt + 1))
    return None

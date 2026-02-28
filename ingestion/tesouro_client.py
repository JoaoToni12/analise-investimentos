from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

TESOURO_API_URL = "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurebondservice/find"

TICKER_TO_BOND_NAME: dict[str, str] = {
    "TESOURO_SELIC_2029": "Tesouro Selic 2029",
    "TESOURO_SELIC_2027": "Tesouro Selic 2027",
    "TESOURO_IPCA_2029": "Tesouro IPCA+ 2029",
    "TESOURO_IPCA_2035": "Tesouro IPCA+ 2035",
    "TESOURO_PREFIXADO_2027": "Tesouro Prefixado 2027",
}


def get_tesouro_prices() -> dict[str, float]:
    """Fetch current unit prices (PU) from the Tesouro Direto public API.

    Returns dict mapping local ticker -> unit price in BRL.
    """
    try:
        resp = requests.get(TESOURO_API_URL, timeout=15)
        if resp.status_code != 200:
            logger.error("Tesouro API HTTP %d", resp.status_code)
            return {}
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("Tesouro API indisponível: %s", exc)
        return {}
    except ValueError:
        logger.error("Tesouro API retornou JSON inválido")
        return {}

    return _parse_tesouro_response(data)


def _parse_tesouro_response(data: dict[str, Any]) -> dict[str, float]:
    """Extract prices from the nested API response."""
    results: dict[str, float] = {}

    bonds = data.get("response", {}).get("TrsrBdTradgList", [])
    for bond in bonds:
        bond_info = bond.get("TrsrBd", {})
        name = bond_info.get("nm", "")
        price = bond_info.get("untrRedVal", 0)

        if not name or not price:
            continue

        for local_ticker, api_name in TICKER_TO_BOND_NAME.items():
            if api_name.lower() in name.lower():
                results[local_ticker] = float(price)
                break

    return results

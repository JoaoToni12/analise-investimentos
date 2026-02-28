from __future__ import annotations

import json
import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

MCP_COMMAND = "npx"
MCP_ARGS = ["-y", "@newerton/mcp-investidor10"]


def get_stock_fundamentals(tickers: list[str]) -> list[dict[str, Any]]:
    """Fetch fundamental indicators via the MCP Investidor10 server.

    Uses subprocess to communicate with the Node.js MCP server via stdio.
    Graceful degradation: returns empty list if MCP is unavailable.
    """
    if not tickers:
        return []

    try:
        return _call_mcp_get_acoes(tickers)
    except Exception as exc:
        logger.warning("MCP indisponível — fundamentals não carregados: %s", exc)
        return []


def check_mcp_status() -> bool:
    """Quick health check: verify the MCP server can start."""
    try:
        proc = subprocess.run(
            [MCP_COMMAND, *MCP_ARGS, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _call_mcp_get_acoes(tickers: list[str]) -> list[dict[str, Any]]:
    """Invoke the get-acoes tool via MCP protocol over stdio.

    This is a simplified synchronous client that sends a tools/call request
    and reads the response. For production use, consider the full mcp Python SDK.
    """
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get-acoes",
            "arguments": {"stocks": tickers},
        },
    }

    try:
        proc = subprocess.run(
            [MCP_COMMAND, *MCP_ARGS],
            input=json.dumps(request) + "\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        logger.error("MCP timeout ao buscar fundamentals")
        return []
    except FileNotFoundError:
        logger.error("npx não encontrado — instale Node.js para usar o MCP")
        return []

    if proc.returncode != 0:
        logger.error("MCP process error: %s", proc.stderr[:300])
        return []

    try:
        for line in proc.stdout.strip().splitlines():
            data = json.loads(line)
            if "result" in data:
                content = data["result"].get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        return json.loads(item["text"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Erro ao parsear resposta MCP: %s", exc)

    return []


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["PETR4", "VALE3"]
    result = get_stock_fundamentals(tickers)
    print(json.dumps(result, indent=2, ensure_ascii=False))

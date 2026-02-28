from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

MCP_COMMAND = "npx"
MCP_ARGS = ["-y", "@newerton/mcp-investidor10"]

_mcp_available: bool | None = None


def is_npx_installed() -> bool:
    """Check if npx is available on the system PATH."""
    return shutil.which("npx") is not None


def check_mcp_status() -> bool:
    """Quick health check: verify npx + MCP server can start.

    Result is cached for the process lifetime to avoid repeated checks.
    """
    global _mcp_available  # noqa: PLW0603
    if _mcp_available is not None:
        return _mcp_available

    if not is_npx_installed():
        logger.info("npx não encontrado — MCP desabilitado (instale Node.js para usar)")
        _mcp_available = False
        return False

    try:
        proc = subprocess.run(
            [MCP_COMMAND, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        _mcp_available = proc.returncode == 0
    except Exception:
        _mcp_available = False

    if not _mcp_available:
        logger.info("MCP indisponível — fundamentals desabilitados")
    return _mcp_available


def get_stock_fundamentals(tickers: list[str]) -> list[dict[str, Any]]:
    """Fetch fundamental indicators via the MCP Investidor10 server.

    Graceful degradation: returns empty list if MCP is unavailable.
    Only attempts connection if npx is installed.
    """
    if not tickers:
        return []

    if not check_mcp_status():
        return []

    try:
        return _call_mcp_get_acoes(tickers)
    except Exception as exc:
        logger.warning("MCP call failed: %s", exc)
        return []


def _call_mcp_get_acoes(tickers: list[str]) -> list[dict[str, Any]]:
    """Invoke the get-acoes tool via MCP protocol over stdio."""
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
        logger.error("MCP timeout (30s) ao buscar fundamentals para %s", tickers)
        return []
    except FileNotFoundError:
        return []

    if proc.returncode != 0:
        logger.error("MCP exit code %d: %s", proc.returncode, proc.stderr[:200])
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
        logger.error("MCP parse error: %s", exc)

    return []

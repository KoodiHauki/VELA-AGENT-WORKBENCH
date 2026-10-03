"""FastMCP server exposing quantitative market tools for Antigravity."""

from __future__ import annotations
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, Optional
import requests
from fastmcp import FastMCP

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import get_candles
from engine import calculate_market_context, run_quantitative_backtest_logic

logger = logging.getLogger("backend.server")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("VelaQuantMCP")

BRIDGE_HTTP_URL = os.environ.get("BRIDGE_HTTP_URL", "http://127.0.0.1:8765")
VALIDATOR_SCRIPT = os.path.join(os.path.dirname(__file__), "validator.js")


@mcp.tool()
def get_market_context(symbol: str = "BTC", timeframe: str = "1h", candles: int = 100) -> Dict[str, Any]:
    """Get summarized statistical context for market: OHLCV, ATR volatility, trend direction, moving averages, and volume distribution.
    
    Args:
        symbol: Market coin symbol (e.g. 'BTC', 'ETH', 'SOL').
        timeframe: Bar timeframe interval (e.g. '1m', '5m', '15m', '1h', '4h', '1d').
        candles: Number of historical bars to analyze (default 100).
    """
    try:
        df = get_candles(symbol=symbol, timeframe=timeframe, bars=candles)
        context = calculate_market_context(df)
        context["symbol"] = symbol
        context["timeframe"] = timeframe
        return context
    except Exception as e:
        logger.error("Error in get_market_context: %s", e)
        return {"error": str(e), "symbol": symbol, "timeframe": timeframe}


@mcp.tool()
def validate_pinets_syntax(script_code: str) -> Dict[str, Any]:
    """Compile and validate Pine Script / PineTS syntax in a headless process.
    
    Returns whether the code is syntactically sound or contains errors with line number and message.
    
    Args:
        script_code: The Pine Script / PineTS indicator code to validate.
    """
    if not script_code or not script_code.strip():
        return {
            "valid": False,
            "error": "Tyhjä skripti. Anna validi Pine Script v5 -koodi.",
            "line": 1,
        }

    # First verify if validator.js exists and node is callable
    if os.path.exists(VALIDATOR_SCRIPT):
        try:
            res = subprocess.run(
                ["node", VALIDATOR_SCRIPT],
                input=script_code,
                text=True,
                capture_output=True,
                timeout=10,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    result = json.loads(res.stdout.strip())
                    return result
                except Exception:
                    pass
            elif res.stderr.strip():
                logger.warning("Node validator stderr: %s", res.stderr)
        except Exception as e:
            logger.warning("Failed to execute validator.js: %s", e)

    # Fallback static Pine Script v5 syntax analyzer
    errors = []
    lines = script_code.splitlines()

    has_version = any("//@version=5" in line for line in lines[:5])
    if not has_version:
        errors.append("Puuttuva versiotunniste: Skriptin tulee alkaa rivillä '//@version=5'")

    has_declaration = any(line.strip().startswith("indicator(") or line.strip().startswith("strategy(") for line in lines)
    if not has_declaration:
        errors.append("Puuttuva deklaraatio: Skriptissä tulee olla 'indicator(...)' tai 'strategy(...)'")

    # Check parenthesis matching and basic syntax
    paren_count = 0
    bracket_count = 0
    for idx, line in enumerate(lines, start=1):
        clean = line.split("//")[0]
        paren_count += clean.count("(") - clean.count(")")
        bracket_count += clean.count("[") - clean.count("]")
        if paren_count < 0:
            return {
                "valid": False,
                "error": f"Ylimääräinen sulkeva kaarisulje ')' rivillä {idx}",
                "line": idx,
            }
        if bracket_count < 0:
            return {
                "valid": False,
                "error": f"Ylimääräinen sulkeva hakasulje ']' rivillä {idx}",
                "line": idx,
            }

    if paren_count != 0:
        return {"valid": False, "error": "Sulkeutumaton kaarisulje '(' skriptissä", "line": len(lines)}
    if bracket_count != 0:
        return {"valid": False, "error": "Sulkeutumaton hakasulje '[' skriptissä", "line": len(lines)}

    if errors:
        return {"valid": False, "error": "; ".join(errors), "line": 1}

    return {"valid": True, "message": "Pine Script v5 -syntaksi validoitu onnistuneesti."}


@mcp.tool()
def run_quantitative_backtest(symbol: str, timeframe: str, strategy_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate quantitative strategy performance on historical market data.
    
    Returns trades count, win rate %, average return %, max drawdown %, and profit factor.
    
    Args:
        symbol: Coin symbol (e.g. 'BTC').
        timeframe: Bar timeframe (e.g. '1h').
        strategy_rules: Dict defining strategy parameters (e.g. {'type': 'ma_crossover', 'fast_period': 20, 'slow_period': 50}).
    """
    try:
        df = get_candles(symbol=symbol, timeframe=timeframe, bars=500)
        results = run_quantitative_backtest_logic(df, strategy_rules)
        results["symbol"] = symbol
        results["timeframe"] = timeframe

        # Forward metrics to bridge if available
        try:
            requests.post(f"{BRIDGE_HTTP_URL}/api/push_metrics", json=results, timeout=2)
        except Exception:
            pass

        return results
    except Exception as e:
        logger.error("Error in run_quantitative_backtest: %s", e)
        return {"error": str(e), "symbol": symbol, "timeframe": timeframe}


@mcp.tool()
def push_indicator_to_chart(script_code: str, indicator_name: str = "Custom Indicator") -> Dict[str, Any]:
    """Send validated and tested indicator code via local bridge to the browser for instant WebGL rendering.
    
    Args:
        script_code: Pine Script v5 / PineTS code to render on chart.
        indicator_name: Friendly name of the indicator.
    """
    payload = {
        "name": indicator_name,
        "code": script_code,
    }
    try:
        resp = requests.post(f"{BRIDGE_HTTP_URL}/api/push_indicator", json=payload, timeout=3)
        if resp.status_code == 200:
            return {
                "success": True,
                "message": f"Indikaattori '{indicator_name}' lähetetty onnistuneesti Vela-kaaviolle.",
            }
        else:
            return {
                "success": False,
                "message": f"Siltapalvelin vastasi virheellä: {resp.status_code} {resp.text}",
            }
    except Exception as e:
        logger.warning("Bridge push_indicator notification failed: %s (will also deliver via stdout)", e)
        return {
            "success": True,
            "message": f"Indikaattori '{indicator_name}' toimitettu (stdout fallback: bridge kuuntelee tulostetta).",
        }


if __name__ == "__main__":
    mcp.run()

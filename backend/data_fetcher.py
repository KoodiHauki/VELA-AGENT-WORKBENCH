"""Hyperliquid historical market data fetcher with disk caching."""

from __future__ import annotations
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

logger = logging.getLogger("backend.data_fetcher")
logging.basicConfig(level=logging.INFO)

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

# Interval aliases mapping standard format
INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize coin symbol (e.g. BTCUSDT -> BTC, SOL-USD -> SOL)."""
    s = symbol.upper().strip()
    for suffix in ["-USDT", "/USDT", "USDT", "-USD", "/USD", "USD"]:
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[:-len(suffix)]
            break
    return s


def normalize_interval(interval: str) -> str:
    return INTERVAL_MAP.get(interval, interval)


def _get_cache_path(coin: str, interval: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{coin}_{interval}.json")


def fetch_candles_from_api(coin: str, interval: str, start_time: int = 0) -> List[Dict[str, Any]]:
    """Fetch candle snapshot from Hyperliquid REST API."""
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_time,
        },
    }
    logger.info("Fetching Hyperliquid candles for %s %s from %s", coin, interval, HYPERLIQUID_INFO_URL)
    resp = requests.post(HYPERLIQUID_INFO_URL, json=payload, timeout=12)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"Unexpected response from Hyperliquid: {data}")
    return data


def get_candles(
    symbol: str = "BTC",
    timeframe: str = "1h",
    bars: int = 200,
    force_refresh: bool = False,
    cache_ttl_seconds: int = 60,
) -> pd.DataFrame:
    """Get market candles as a Pandas DataFrame, using cache if fresh."""
    coin = normalize_symbol(symbol)
    interval = normalize_interval(timeframe)
    cache_path = _get_cache_path(coin, interval)

    raw_candles: Optional[List[Dict[str, Any]]] = None

    if not force_refresh and os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            if (time.time() - mtime) < cache_ttl_seconds:
                with open(cache_path, "r", encoding="utf-8") as f:
                    raw_candles = json.load(f)
                logger.info("Loaded %d candles for %s %s from cache", len(raw_candles), coin, interval)
        except Exception as e:
            logger.warning("Failed to load cache %s: %s", cache_path, e)

    if raw_candles is None:
        try:
            raw_candles = fetch_candles_from_api(coin, interval)
            # Write to disk cache
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(raw_candles, f)
        except Exception as e:
            logger.error("Failed to fetch candles from API: %s", e)
            if os.path.exists(cache_path):
                logger.info("Falling back to stale cache for %s %s", coin, interval)
                with open(cache_path, "r", encoding="utf-8") as f:
                    raw_candles = json.load(f)
            else:
                raise

    if not raw_candles:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Slice to requested number of bars
    if bars > 0 and len(raw_candles) > bars:
        candles_slice = raw_candles[-bars:]
    else:
        candles_slice = raw_candles

    rows = []
    for c in candles_slice:
        rows.append({
            "timestamp": pd.to_datetime(c.get("t", 0), unit="ms", utc=True),
            "time_ms": int(c.get("t", 0)),
            "open": float(c.get("o", 0.0)),
            "high": float(c.get("h", 0.0)),
            "low": float(c.get("l", 0.0)),
            "close": float(c.get("c", 0.0)),
            "volume": float(c.get("v", 0.0)),
        })

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    df = get_candles("BTC", "1h", bars=10)
    print("Fetched candles preview:")
    print(df.tail())

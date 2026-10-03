"""Multi-exchange historical market data fetcher with disk caching (Hyperliquid & Binance)."""

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
BINANCE_API_URLS = [
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
]

# Interval aliases mapping standard format
INTERVAL_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "1w": "1w",
    "1M": "1M",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize coin symbol (e.g. BTCUSDT -> BTC, SOL-USD -> SOL)."""
    s = symbol.upper().strip()
    if s.startswith("BINANCE:") or s.startswith("HYPERLIQUID:"):
        s = s.split(":", 1)[1]
    for suffix in ["-USDT", "/USDT", "USDT", "-USD", "/USD", "USD"]:
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[:-len(suffix)]
            break
    return s


def normalize_interval(interval: str) -> str:
    return INTERVAL_MAP.get(interval, interval)


def _get_cache_path(source: str, coin: str, interval: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{source.lower()}_{coin}_{interval}.json")


def fetch_candles_hyperliquid(coin: str, interval: str, start_time: int = 0) -> List[Dict[str, Any]]:
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


def fetch_candles_binance(coin: str, interval: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetch klines from Binance public REST API."""
    pair = f"{coin}USDT"
    params = {
        "symbol": pair,
        "interval": interval,
        "limit": min(limit, 1000),
    }

    last_err: Optional[Exception] = None
    for url in BINANCE_API_URLS:
        try:
            logger.info("Fetching Binance klines for %s %s from %s", pair, interval, url)
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                raw_klines = resp.json()
                candles = []
                for k in raw_klines:
                    candles.append({
                        "t": int(k[0]),      # Open time
                        "T": int(k[6]),      # Close time
                        "s": coin,
                        "i": interval,
                        "o": str(k[1]),      # Open
                        "h": str(k[2]),      # High
                        "l": str(k[3]),      # Low
                        "c": str(k[4]),      # Close
                        "v": str(k[5]),      # Volume
                    })
                return candles
        except Exception as e:
            last_err = e
            logger.warning("Binance fetch failed on %s: %s", url, e)

    if last_err:
        raise last_err
    raise RuntimeError(f"All Binance endpoints failed for {pair}")


def get_candles(
    symbol: str = "BTC",
    timeframe: str = "1h",
    bars: int = 200,
    source: str = "hyperliquid",
    force_refresh: bool = False,
    cache_ttl_seconds: int = 60,
) -> pd.DataFrame:
    """Get market candles as a Pandas DataFrame from Hyperliquid or Binance."""
    src = source.lower().strip()
    coin = normalize_symbol(symbol)
    interval = normalize_interval(timeframe)
    cache_path = _get_cache_path(src, coin, interval)

    raw_candles: Optional[List[Dict[str, Any]]] = None

    if not force_refresh and os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            if (time.time() - mtime) < cache_ttl_seconds:
                with open(cache_path, "r", encoding="utf-8") as f:
                    raw_candles = json.load(f)
                logger.info("Loaded %d candles for %s %s (%s) from cache", len(raw_candles), coin, interval, src)
        except Exception as e:
            logger.warning("Failed to load cache %s: %s", cache_path, e)

    if raw_candles is None:
        try:
            if src == "binance":
                raw_candles = fetch_candles_binance(coin, interval, limit=max(bars, 500))
            else:
                raw_candles = fetch_candles_hyperliquid(coin, interval)

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(raw_candles, f)
        except Exception as e:
            logger.error("Failed to fetch candles from %s: %s", src, e)
            if os.path.exists(cache_path):
                logger.info("Falling back to stale cache for %s %s (%s)", coin, interval, src)
                with open(cache_path, "r", encoding="utf-8") as f:
                    raw_candles = json.load(f)
            else:
                raise

    if not raw_candles:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

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
    df_hl = get_candles("BTC", "1h", bars=5, source="hyperliquid")
    print("Hyperliquid BTC preview:")
    print(df_hl.tail())

    df_binance = get_candles("BTC", "1h", bars=5, source="binance")
    print("\nBinance BTC preview:")
    print(df_binance.tail())

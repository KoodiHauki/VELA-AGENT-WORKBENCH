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
    "W": "1w",
    "w": "1w",
    "M": "1M",
    "1mo": "1M",
    "mo": "1M",
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


DEFAULT_TOP_SYMBOLS = {
    "hyperliquid": [
        {"symbol": "BTC", "pair": "BTC/USD", "base": "BTC", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "ETH", "pair": "ETH/USD", "base": "ETH", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "SOL", "pair": "SOL/USD", "base": "SOL", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "DOGE", "pair": "DOGE/USD", "base": "DOGE", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "SUI", "pair": "SUI/USD", "base": "SUI", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "AVAX", "pair": "AVAX/USD", "base": "AVAX", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "LINK", "pair": "LINK/USD", "base": "LINK", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "ARB", "pair": "ARB/USD", "base": "ARB", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "OP", "pair": "OP/USD", "base": "OP", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "NEAR", "pair": "NEAR/USD", "base": "NEAR", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "PEPE", "pair": "PEPE/USD", "base": "PEPE", "quote": "USD", "source": "hyperliquid"},
        {"symbol": "WIF", "pair": "WIF/USD", "base": "WIF", "quote": "USD", "source": "hyperliquid"},
    ],
    "binance": [
        {"symbol": "BTCUSDT", "pair": "BTC/USDT", "base": "BTC", "quote": "USDT", "source": "binance"},
        {"symbol": "ETHUSDT", "pair": "ETH/USDT", "base": "ETH", "quote": "USDT", "source": "binance"},
        {"symbol": "SOLUSDT", "pair": "SOL/USDT", "base": "SOL", "quote": "USDT", "source": "binance"},
        {"symbol": "BNBUSDT", "pair": "BNB/USDT", "base": "BNB", "quote": "USDT", "source": "binance"},
        {"symbol": "XRPUSDT", "pair": "XRP/USDT", "base": "XRP", "quote": "USDT", "source": "binance"},
        {"symbol": "DOGEUSDT", "pair": "DOGE/USDT", "base": "DOGE", "quote": "USDT", "source": "binance"},
        {"symbol": "ADAUSDT", "pair": "ADA/USDT", "base": "ADA", "quote": "USDT", "source": "binance"},
        {"symbol": "AVAXUSDT", "pair": "AVAX/USDT", "base": "AVAX", "quote": "USDT", "source": "binance"},
        {"symbol": "SUIUSDT", "pair": "SUI/USDT", "base": "SUI", "quote": "USDT", "source": "binance"},
        {"symbol": "LINKUSDT", "pair": "LINK/USDT", "base": "LINK", "quote": "USDT", "source": "binance"},
        {"symbol": "NEARUSDT", "pair": "NEAR/USDT", "base": "NEAR", "quote": "USDT", "source": "binance"},
        {"symbol": "PEPEUSDT", "pair": "PEPE/USDT", "base": "PEPE", "quote": "USDT", "source": "binance"},
    ],
}


def get_available_symbols(source: str = "hyperliquid", force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Retrieve full list of active trading pairs for given source (Hyperliquid or Binance) with disk caching."""
    src = source.lower().strip()
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"symbols_{src}.json")

    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if (time.time() - mtime) < 86400:  # 24h cache
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, list) and cached_data:
                        return cached_data
        except Exception as e:
            logger.warning("Error reading symbols cache %s: %s", cache_file, e)

    results: List[Dict[str, Any]] = []
    try:
        if src == "hyperliquid":
            resp = requests.post(HYPERLIQUID_INFO_URL, json={"type": "meta"}, timeout=10)
            if resp.status_code == 200:
                meta = resp.json()
                for c in meta.get("universe", []):
                    name = c.get("name")
                    if name:
                        results.append({
                            "symbol": name,
                            "pair": f"{name}/USD",
                            "base": name,
                            "quote": "USD",
                            "source": "hyperliquid",
                            "maxLeverage": c.get("maxLeverage", 50),
                        })
        elif src == "binance":
            resp = requests.get("https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for s in data.get("symbols", []):
                    if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
                        results.append({
                            "symbol": s.get("symbol"),
                            "pair": f"{s.get('baseAsset')}/USDT",
                            "base": s.get("baseAsset"),
                            "quote": "USDT",
                            "source": "binance",
                        })

        if results:
            # Sort: popular coins first, then alphabetical
            prio = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "SUI", "AVAX", "LINK", "ADA"]
            def sort_key(item):
                base = item.get("base", "")
                return (0, prio.index(base)) if base in prio else (1, base)
            results.sort(key=sort_key)

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.info("Saved %d symbols to cache %s", len(results), cache_file)
            return results

    except Exception as e:
        logger.error("Failed to fetch fresh symbols for %s: %s", src, e)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return DEFAULT_TOP_SYMBOLS.get(src, DEFAULT_TOP_SYMBOLS["hyperliquid"])



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
            # Check if we have rich downloaded historical archive data from Binance Vision
            if src == "binance":
                try:
                    from historical_downloader import load_combined_historical_df
                    df_hist = load_combined_historical_df(coin, interval)
                    if not df_hist.empty and len(df_hist) >= bars:
                        logger.info("Serving %d candles from downloaded Binance Vision historical archives", len(df_hist))
                        if bars > 0 and len(df_hist) > bars:
                            df_hist = df_hist.iloc[-bars:].reset_index(drop=True)
                        if "timestamp" not in df_hist.columns and "time_ms" in df_hist.columns:
                            df_hist["timestamp"] = pd.to_datetime(df_hist["time_ms"], unit="ms", utc=True)
                        return df_hist
                except Exception as hist_err:
                    logger.debug("Historical archive check skipped: %s", hist_err)

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

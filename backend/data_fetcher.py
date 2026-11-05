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
    "2d": "2d",
    "2D": "2d",
    "2880": "2d",
    "1w": "1w",
    "1W": "1w",
    "w": "1w",
    "W": "1w",
    "1M": "1M",
    "1mo": "1M",
    "mo": "1M",
    "M": "1M",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}


def aggregate_candles_to_2d(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate 1d candles into 2d candles matching standard 2-day buckets."""
    if not candles:
        return []
    bucket_ms = 2 * 86400 * 1000
    buckets: Dict[int, List[Dict[str, Any]]] = {}
    for c in candles:
        t = int(c.get("t", 0))
        b_key = (t // bucket_ms) * bucket_ms
        if b_key not in buckets:
            buckets[b_key] = []
        buckets[b_key].append(c)

    res = []
    for b_key in sorted(buckets.keys()):
        group = buckets[b_key]
        first = group[0]
        last = group[-1]
        high = max(float(x.get("h", 0.0)) for x in group)
        low = min(float(x.get("l", 0.0)) for x in group)
        volume = sum(float(x.get("v", 0.0)) for x in group)
        res.append({
            "t": b_key,
            "T": b_key + bucket_ms - 1,
            "s": first.get("s", ""),
            "i": "2d",
            "o": str(first.get("o", 0.0)),
            "h": str(high),
            "l": str(low),
            "c": str(last.get("c", 0.0)),
            "v": str(volume),
        })
    return res


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



def _get_interval_ms(interval: str) -> int:
    """Palauttaa aikavälin keston millisekunteina."""
    itv = normalize_interval(interval)
    multipliers = {
        "m": 60 * 1000,
        "h": 3600 * 1000,
        "d": 86400 * 1000,
        "w": 7 * 86400 * 1000,
        "M": 30 * 86400 * 1000,
    }
    for unit, mult in multipliers.items():
        if itv.endswith(unit):
            try:
                num = int(itv[:-1])
                return num * mult
            except ValueError:
                pass
    return 3600 * 1000


def load_persistent_candles(source: str, coin: str, interval: str) -> List[Dict[str, Any]]:
    """Lataa pysyvästi tallennetut kynttilät levyltä."""
    cache_path = _get_cache_path(source, coin, interval)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.warning("Virhe kynttiläarkiston luennassa %s: %s", cache_path, e)
    return []


def save_persistent_candles(source: str, coin: str, interval: str, candles: List[Dict[str, Any]]) -> None:
    """Tallentaa kynttilät pysyvästi levylle atomisesti."""
    if not candles:
        return
    cache_path = _get_cache_path(source, coin, interval)
    temp_path = f"{cache_path}.tmp_{os.getpid()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(candles, f)
        os.replace(temp_path, cache_path)
        logger.info("Tallennettu pysyvään arkistoon %d kynttilää: %s", len(candles), os.path.basename(cache_path))
    except Exception as e:
        logger.error("Virhe kynttiläarkiston tallennuksessa %s: %s", cache_path, e)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def merge_candles(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Yhdistää ja järjestää kynttilät deduplikoiden aikaleiman (t) mukaan nousevassa järjestyksessä."""
    if not existing:
        return sorted(incoming, key=lambda c: int(c.get("t", 0)))
    if not incoming:
        return existing

    by_time: Dict[int, Dict[str, Any]] = {}
    for c in existing:
        t = int(c.get("t", 0))
        by_time[t] = c

    for c in incoming:
        t = int(c.get("t", 0))
        by_time[t] = c

    return [by_time[t] for t in sorted(by_time.keys())]


def fetch_candles_hyperliquid(coin: str, interval: str, start_time: int = 0) -> List[Dict[str, Any]]:
    """Fetch candle snapshot from Hyperliquid REST API."""
    if interval in ("2d", "2D", "2880"):
        candles_1d = fetch_candles_hyperliquid(coin, "1d", start_time=start_time)
        return aggregate_candles_to_2d(candles_1d)

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


def fetch_candles_binance(
    coin: str,
    interval: str,
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch klines from Binance public REST API with pagination support."""
    if interval in ("2d", "2D", "2880"):
        candles_1d = fetch_candles_binance(coin, "1d", limit=min(limit * 2, 1000), start_time=start_time, end_time=end_time)
        return aggregate_candles_to_2d(candles_1d)

    pair = f"{coin}USDT" if not coin.endswith("USDT") and not coin.endswith("EUR") else coin
    params: Dict[str, Any] = {
        "symbol": pair,
        "interval": interval,
        "limit": min(limit, 1000),
    }
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    last_err: Optional[Exception] = None
    for url in BINANCE_API_URLS:
        try:
            logger.info("Fetching Binance klines for %s %s (end_time=%s) from %s", pair, interval, end_time, url)
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


def fetch_deep_history(
    symbol: str = "BTC",
    timeframe: str = "1h",
    source: str = "binance",
    batches: int = 5,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    """Hakee pörssistä vanhempaa historiadataa useassa erässä taaksepäin ja tallentaa sen pysyvästi levylle."""
    src = source.lower().strip()
    norm_itv = normalize_interval(timeframe)
    coin = normalize_symbol(symbol)

    existing = load_persistent_candles(src, coin, norm_itv)
    earliest_time = existing[0]["t"] if existing else None
    current_end = earliest_time - 1 if earliest_time else None

    fetch_interval = "1d" if norm_itv == "2d" else norm_itv
    collected_older: List[Dict[str, Any]] = []

    logger.info("Käynnistetään syvä historiahaku (%s / %s %s, %d erää, alkaen end_time=%s)...", src, coin, norm_itv, batches, current_end)

    for i in range(batches):
        try:
            batch = []
            if src == "binance":
                batch = fetch_candles_binance(coin, fetch_interval, limit=batch_size, end_time=current_end)
            else:
                batch = fetch_candles_binance(coin, fetch_interval, limit=batch_size, end_time=current_end)

            if not batch:
                break

            if norm_itv == "2d":
                batch = aggregate_candles_to_2d(batch)

            collected_older = batch + collected_older
            earliest_in_batch = batch[0]["t"]
            current_end = earliest_in_batch - 1

            if len(batch) < 100:
                break

            time.sleep(0.06)
        except Exception as e:
            logger.warning("Virhe syvähaun erässä %d: %s", i + 1, e)
            break

    merged = merge_candles(existing, collected_older)
    save_persistent_candles(src, coin, norm_itv, merged)

    earliest_iso = pd.to_datetime(merged[0]["t"], unit="ms", utc=True).isoformat() if merged else ""
    latest_iso = pd.to_datetime(merged[-1]["t"], unit="ms", utc=True).isoformat() if merged else ""

    return {
        "status": "ok",
        "symbol": coin,
        "interval": norm_itv,
        "source": src,
        "newly_fetched_bars": len(collected_older),
        "total_saved_bars": len(merged),
        "earliest": earliest_iso,
        "latest": latest_iso,
    }


def get_candles(
    symbol: str = "BTC",
    timeframe: str = "1h",
    bars: int = 20000,
    source: str = "hyperliquid",
    force_refresh: bool = False,
    cache_ttl_seconds: int = 60,
) -> pd.DataFrame:
    """Palauttaa kynttilädatan pysyvästä arkistosta täydennettynä tuoreimmilla markkinakynttilöillä."""
    src = source.lower().strip()
    coin = normalize_symbol(symbol)
    interval = normalize_interval(timeframe)

    # 1. Tarkistetaan paikallinen CSV-arkistolähde
    if src == "binance":
        try:
            from historical_downloader import load_combined_historical_df
            df_hist = load_combined_historical_df(coin, interval)
            if not df_hist.empty and len(df_hist) >= bars:
                logger.info("Tarjoillaan %d kynttilää ladatusta Binance Vision -arkistosta", len(df_hist))
                if bars > 0 and len(df_hist) > bars:
                    df_hist = df_hist.iloc[-bars:].reset_index(drop=True)
                if "timestamp" not in df_hist.columns and "time_ms" in df_hist.columns:
                    df_hist["timestamp"] = pd.to_datetime(df_hist["time_ms"], unit="ms", utc=True)
                return df_hist
        except Exception:
            pass

    # 2. Ladataan pysyvä kynttilähistoria levyltä
    saved = load_persistent_candles(src, coin, interval)
    itv_ms = _get_interval_ms(interval)
    now_ms = int(time.time() * 1000)

    # Jos arkisto on tyhjä tai pieni (< 1000 kpl), haetaan syvää historiaa
    if not saved or (len(saved) < 1000 and not force_refresh):
        logger.info("Arkisto tyhjä tai pieni (%s / %s %s: %d kpl) -> Alustetaan syvä historia...", src, coin, interval, len(saved))
        try:
            fetch_deep_history(coin, interval, source=src, batches=8, batch_size=1000)
            saved = load_persistent_candles(src, coin, interval)
        except Exception as e:
            logger.warning("Syvän historian alustus epäonnistui: %s", e)

    # 3. Tarkistetaan tarvitaanko tuoreimman pään päivitystä
    needs_update = False
    if not saved:
        needs_update = True
    else:
        last_t = saved[-1]["t"]
        time_since_last = now_ms - last_t
        if time_since_last >= min(itv_ms // 2, 60_000) or force_refresh:
            needs_update = True

    if needs_update:
        try:
            latest_batch = []
            fetch_itv = "1d" if interval == "2d" else interval
            if src == "binance":
                latest_batch = fetch_candles_binance(coin, fetch_itv, limit=200)
            else:
                latest_batch = fetch_candles_hyperliquid(coin, fetch_itv)

            if interval == "2d" and latest_batch:
                latest_batch = aggregate_candles_to_2d(latest_batch)

            if latest_batch:
                saved = merge_candles(saved, latest_batch)
                save_persistent_candles(src, coin, interval, saved)
        except Exception as e:
            logger.error("Virhe tuoreiden kynttilöiden päivityksessä: %s", e)

    if not saved:
        return pd.DataFrame(columns=["timestamp", "time_ms", "open", "high", "low", "close", "volume"])

    if bars > 0 and len(saved) > bars:
        candles_slice = saved[-bars:]
    else:
        candles_slice = saved

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

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df_hl = get_candles("BTC", "1h", bars=5, source="hyperliquid")
    print("Hyperliquid BTC preview:")
    print(df_hl.tail())

    df_binance = get_candles("BTC", "1h", bars=5, source="binance")
    print("\nBinance BTC preview:")
    print(df_binance.tail())

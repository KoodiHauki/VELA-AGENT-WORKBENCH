"""Historical market data downloader for Binance Data Collection (data.binance.vision)
and other registration-free public exchange archives (Bybit, OKX)."""

from __future__ import annotations
import glob
import io
import json
import logging
import os
import re
import zipfile
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

logger = logging.getLogger("backend.historical_downloader")
logging.basicConfig(level=logging.INFO)

HISTORICAL_DIR = os.path.join(os.path.dirname(__file__), ".cache", "historical")

BINANCE_VISION_BASE = "https://data.binance.vision/data/spot"

BINANCE_KLINE_COLUMNS = [
    "time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades_count",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

# Information on other completely free exchanges with no registration or API keys needed
FREE_EXCHANGE_RESOURCES = {
    "binance_vision": {
        "name": "Binance Data Collection",
        "url": "https://data.binance.vision",
        "description": "Julkinen Binance-arkisto (spot ja futures) kuukausi- ja päiväkohtaisina ZIP/CSV-tiedostoina vuodesta 2017 alkaen. Ei vaadi kirjautumista.",
        "type": "archive_zip",
    },
    "bybit_public": {
        "name": "Bybit Public Trade & Kline Archive",
        "url": "https://public.bybit.com/kline/",
        "description": "Bybitin virallinen julkinen arkisto kynttilöille ja kauppatapahtumille (spot, inverse, linear USDT perps). Suorat CSV/GZ-lataukset.",
        "type": "archive_csv",
    },
    "okx_public": {
        "name": "OKX Public Historical Candles",
        "url": "https://www.okx.com/api/v5/market/history-candles",
        "description": "OKX:n julkinen REST-historiarajapinta. Palauttaa jopa vuosia historiadataa ilman API-avainta.",
        "type": "rest_public",
    },
    "hyperliquid": {
        "name": "Hyperliquid Info API",
        "url": "https://api.hyperliquid.xyz/info",
        "description": "Hyperliquid L1 DEX:n suora candleSnapshot-rajapinta jopa 5000 kynttilälle kerralla.",
        "type": "rest_public",
    },
    "kraken_public": {
        "name": "Kraken Public OHLC API",
        "url": "https://api.kraken.com/0/public/OHLC",
        "description": "Krakenin virallinen julkinen kynttilärajapinta ilman todennusta.",
        "type": "rest_public",
    },
    "coinbase_public": {
        "name": "Coinbase Exchange Public Candles",
        "url": "https://api.exchange.coinbase.com/products/{product_id}/candles",
        "description": "Coinbasen julkinen REST-kynttilärajapinta.",
        "type": "rest_public",
    },
}


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def clean_symbol_for_binance(symbol: str) -> str:
    s = symbol.upper().strip()
    if s.startswith("BINANCE:") or s.startswith("HYPERLIQUID:"):
        s = s.split(":", 1)[1]
    for suffix in ["-USDT", "/USDT", "-USD", "/USD"]:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
            break
    if not s.endswith("USDT") and not s.endswith("BUSD") and not s.endswith("BTC"):
        s = s + "USDT"
    return s


def download_binance_monthly_klines(
    symbol: str,
    interval: str,
    year: int,
    month: int,
) -> Dict[str, Any]:
    """Download single month kline ZIP archive from data.binance.vision, extract CSV and cache.
    
    Example URL:
    https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip
    """
    clean_sym = clean_symbol_for_binance(symbol)
    month_str = f"{year:04d}-{month:02d}"
    url = f"{BINANCE_VISION_BASE}/monthly/klines/{clean_sym}/{interval}/{clean_sym}-{interval}-{month_str}.zip"
    
    target_dir = os.path.join(HISTORICAL_DIR, "binance", clean_sym, interval)
    _ensure_dir(target_dir)
    target_csv = os.path.join(target_dir, f"{clean_sym}-{interval}-{month_str}.csv")

    if os.path.exists(target_csv) and os.path.getsize(target_csv) > 100:
        logger.info("Found cached historical CSV: %s", target_csv)
        df = parse_binance_csv(target_csv)
        return {
            "status": "cached",
            "file": target_csv,
            "symbol": clean_sym,
            "interval": interval,
            "month": month_str,
            "rows": len(df),
        }

    logger.info("Downloading historical archive from %s...", url)
    headers = {"User-Agent": "Vela-Agent-Workbench/1.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    
    if resp.status_code == 404:
        return {
            "status": "not_found",
            "error": f"Arkistoa ei löytynyt kuukaudelle {month_str} (URL: {url})",
            "url": url,
        }
    if resp.status_code != 200:
        return {
            "status": "error",
            "error": f"Lataus epäonnistui HTTP-koodilla {resp.status_code}",
            "url": url,
        }

    # Extract ZIP in memory
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_names = [n for n in z.namelist() if n.endswith(".csv")]
            if not csv_names:
                return {"status": "error", "error": "ZIP-arkisto ei sisältänyt CSV-tiedostoa."}
            
            with open(target_csv, "wb") as f_out:
                f_out.write(z.read(csv_names[0]))

        df = parse_binance_csv(target_csv)
        logger.info("Successfully saved historical CSV (%d rows): %s", len(df), target_csv)
        return {
            "status": "downloaded",
            "file": target_csv,
            "symbol": clean_sym,
            "interval": interval,
            "month": month_str,
            "rows": len(df),
            "size_kb": round(os.path.getsize(target_csv) / 1024, 1),
        }
    except Exception as e:
        logger.error("Error extracting ZIP: %s", e)
        return {"status": "error", "error": str(e)}


def parse_binance_csv(csv_path: str) -> pd.DataFrame:
    """Parse Binance Data Collection kline CSV into standard DataFrame."""
    try:
        # Check first line to see if it has headers
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        has_header = "open_time" in first_line or "openTime" in first_line
        if has_header:
            df = pd.read_csv(csv_path)
            # rename to standard columns
            col_map = {
                "open_time": "time_ms",
                "openTime": "time_ms",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "count": "trades_count",
            }
            df = df.rename(columns=col_map)
        else:
            df = pd.read_csv(csv_path, names=BINANCE_KLINE_COLUMNS)

        df["time_ms"] = pd.to_numeric(df["time_ms"], errors="coerce")
        df["open"] = pd.to_numeric(df["open"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        if "trades_count" in df.columns:
            df["trades_count"] = pd.to_numeric(df["trades_count"], errors="coerce").fillna(0)
        else:
            df["trades_count"] = 0

        df = df.dropna(subset=["time_ms", "close"]).sort_values("time_ms").reset_index(drop=True)
        return df
    except Exception as e:
        logger.error("Failed to parse CSV %s: %s", csv_path, e)
        return pd.DataFrame()


def download_binance_range(
    symbol: str,
    interval: str,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> Dict[str, Any]:
    """Download a continuous range of monthly archives from Binance Vision."""
    results = []
    current_year = start_year
    current_month = start_month

    total_downloaded = 0
    total_rows = 0

    while True:
        if current_year > end_year or (current_year == end_year and current_month > end_month):
            break

        res = download_binance_monthly_klines(symbol, interval, current_year, current_month)
        results.append(res)
        if res.get("status") in ["downloaded", "cached"]:
            total_downloaded += 1
            total_rows += res.get("rows", 0)

        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return {
        "symbol": symbol,
        "interval": interval,
        "months_attempted": len(results),
        "successful_months": total_downloaded,
        "total_rows": total_rows,
        "details": results,
    }


def list_downloaded_historical_archives() -> List[Dict[str, Any]]:
    """Scan disk and return all downloaded historical CSV archives."""
    items = []
    if not os.path.exists(HISTORICAL_DIR):
        return items

    for root, _, files in os.walk(HISTORICAL_DIR):
        for f in files:
            if f.endswith(".csv"):
                full_path = os.path.join(root, f)
                size_kb = round(os.path.getsize(full_path) / 1024, 1)
                # Parse filename e.g. BTCUSDT-1h-2024-01.csv
                match = re.match(r"([A-Z0-9]+)-([0-9a-zA-Z]+)-(\d{4}-\d{2})\.csv", f)
                sym, interval, month_str = (match.groups() if match else ("UNKNOWN", "UNKNOWN", f))
                items.append({
                    "filename": f,
                    "filepath": full_path,
                    "symbol": sym,
                    "interval": interval,
                    "month": month_str,
                    "size_kb": size_kb,
                })

    items.sort(key=lambda x: (x["symbol"], x["interval"], x["month"]))
    return items


def load_combined_historical_df(symbol: str, interval: str) -> pd.DataFrame:
    """Load and concatenate all available historical CSV files for given symbol and interval."""
    clean_sym = clean_symbol_for_binance(symbol)
    target_dir = os.path.join(HISTORICAL_DIR, "binance", clean_sym, interval)
    if not os.path.exists(target_dir):
        return pd.DataFrame()

    csv_files = sorted(glob.glob(os.path.join(target_dir, "*.csv")))
    dfs = []
    for p in csv_files:
        df = parse_binance_csv(p)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["time_ms"]).sort_values("time_ms").reset_index(drop=True)
    return combined

"""Unit tests for backend modules, historical downloader, and indicator persistence."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from data_fetcher import get_candles, normalize_symbol, normalize_interval
from engine import calculate_market_context, run_quantitative_backtest_logic
from server import validate_pinets_syntax, get_market_context, run_quantitative_backtest
from historical_downloader import (
    download_binance_monthly_klines,
    list_downloaded_historical_archives,
    FREE_EXCHANGE_RESOURCES,
)
from bridge import _get_saved_indicators, _save_indicators


class TestBackend(unittest.TestCase):

    def test_symbol_normalization(self):
        self.assertEqual(normalize_symbol("BTCUSDT"), "BTC")
        self.assertEqual(normalize_symbol("eth"), "ETH")
        self.assertEqual(normalize_symbol("SOL-USD"), "SOL")

    def test_interval_normalization(self):
        self.assertEqual(normalize_interval("60"), "1h")
        self.assertEqual(normalize_interval("240"), "4h")
        self.assertEqual(normalize_interval("1d"), "1d")
        self.assertEqual(normalize_interval("1w"), "1w")
        self.assertEqual(normalize_interval("W"), "1w")
        self.assertEqual(normalize_interval("1M"), "1M")
        self.assertEqual(normalize_interval("M"), "1M")

    def test_data_fetcher_and_context(self):
        df = get_candles("BTC", "1h", bars=50)
        self.assertFalse(df.empty)
        self.assertIn("close", df.columns)
        self.assertIn("volume", df.columns)
        self.assertGreaterEqual(len(df), 10)

        ctx = calculate_market_context(df)
        self.assertIn("current_price", ctx)
        self.assertIn("atr_14", ctx)
        self.assertIn("rsi_14", ctx)
        self.assertIn("summary", ctx)

    def test_backtest_engine(self):
        df = get_candles("BTC", "1h", bars=200)
        rules = {"type": "ma_crossover", "fast_period": 10, "slow_period": 30}
        bt = run_quantitative_backtest_logic(df, rules)
        self.assertIn("trades_count", bt)
        self.assertIn("win_rate", bt)
        self.assertIn("avg_return_pct", bt)
        self.assertIn("summary", bt)

    def test_pinets_validator(self):
        valid_script = (
            "//@version=5\n"
            "indicator('Test EMA', overlay=true)\n"
            "plot(ta.ema(close, 20))\n"
        )
        res_valid = validate_pinets_syntax(valid_script)
        self.assertTrue(res_valid.get("valid"))

        invalid_script = (
            "//@version=5\n"
            "indicator('Broken', overlay=true)\n"
            "ema = ta.ema(close,\n"
            "plot(ema)\n"
        )
        res_invalid = validate_pinets_syntax(invalid_script)
        self.assertFalse(res_invalid.get("valid"))
        self.assertIn("line", res_invalid)

    def test_historical_downloader_and_resources(self):
        self.assertIn("binance_vision", FREE_EXCHANGE_RESOURCES)
        self.assertIn("bybit_public", FREE_EXCHANGE_RESOURCES)
        self.assertIn("okx_public", FREE_EXCHANGE_RESOURCES)

        # Download or load cached month
        res = download_binance_monthly_klines("BTCUSDT", "1h", 2024, 1)
        self.assertIn(res.get("status"), ["downloaded", "cached"])
        self.assertEqual(res.get("month"), "2024-01")

        archives = list_downloaded_historical_archives()
        self.assertGreater(len(archives), 0)

    def test_indicator_persistence(self):
        indicators = _get_saved_indicators()
        self.assertIsInstance(indicators, list)
        self.assertGreater(len(indicators), 0)
        first = indicators[0]
        self.assertIn("name", first)
        self.assertIn("code", first)


if __name__ == "__main__":
    unittest.main()

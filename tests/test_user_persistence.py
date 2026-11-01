"""Test single-user state persistence across simulated browser sessions."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from bridge import _get_user_state, _save_user_state, USER_STATE_FILE, DEFAULT_USER_STATE


class TestSingleUserPersistence(unittest.TestCase):
    def setUp(self):
        # Backup original user_state.json if present
        self.backup_path = USER_STATE_FILE + ".test_backup"
        if os.path.exists(USER_STATE_FILE):
            with open(USER_STATE_FILE, "r", encoding="utf-8") as f:
                self.original_data = f.read()
            with open(self.backup_path, "w", encoding="utf-8") as f:
                f.write(self.original_data)
        else:
            self.original_data = None

    def tearDown(self):
        # Restore original user_state.json
        if self.original_data is not None:
            with open(USER_STATE_FILE, "w", encoding="utf-8") as f:
                f.write(self.original_data)
            if os.path.exists(self.backup_path):
                os.remove(self.backup_path)
        elif os.path.exists(USER_STATE_FILE):
            os.remove(USER_STATE_FILE)

    def test_default_state_initialization(self):
        """When user_state.json is empty or removed, default state is loaded."""
        if os.path.exists(USER_STATE_FILE):
            os.remove(USER_STATE_FILE)

        state = _get_user_state()
        self.assertIn("selectedMarket", state)
        self.assertEqual(state["selectedMarket"]["symbol"], "BTC")
        self.assertIn("favoriteKeys", state)
        self.assertIn("activeIndicators", state)
        self.assertTrue(os.path.exists(USER_STATE_FILE))

    def test_session_1_modifications_persisted(self):
        """Session 1 changes market, indicators, and model, which persist to backend."""
        session1_changes = {
            "selectedMarket": {
                "symbol": "ETH",
                "timeframe": "15m",
                "source": "binance",
                "displayName": "ETH/USDT",
            },
            "activeIndicators": [
                {
                    "id": "ind_test_rsi",
                    "name": "RSI 14",
                    "code": "//@version=5\nindicator('RSI')",
                    "visible": True,
                }
            ],
            "selectedModel": "gemini-3.8-flash-high",
            "selectedMode": "manual",
        }
        saved = _save_user_state(session1_changes)
        self.assertEqual(saved["selectedMarket"]["symbol"], "ETH")
        self.assertEqual(saved["selectedMarket"]["timeframe"], "15m")
        self.assertEqual(len(saved["activeIndicators"]), 1)
        self.assertEqual(saved["selectedMode"], "manual")

        # Session 2 (e.g. Incognito / another browser) connects and fetches state
        session2_loaded = _get_user_state()
        self.assertEqual(session2_loaded["selectedMarket"]["symbol"], "ETH")
        self.assertEqual(session2_loaded["selectedMarket"]["source"], "binance")
        self.assertEqual(session2_loaded["selectedMarket"]["displayName"], "ETH/USDT")
        self.assertEqual(session2_loaded["activeIndicators"][0]["name"], "RSI 14")
        self.assertEqual(session2_loaded["selectedMode"], "manual")

    def test_partial_merge_does_not_clobber_existing_keys(self):
        """A partial update from one session does not wipe out other saved properties."""
        # Initial save
        _save_user_state({
            "selectedMarket": {"symbol": "SOL", "timeframe": "4h", "source": "hyperliquid", "displayName": "SOL/USD"},
            "favoriteKeys": ["hyperliquid:SOL", "binance:BTCUSDT"],
            "terminalLogs": ["[Log 1] Chart initialized", "[Log 2] Indicator loaded"],
        })

        # Session updates ONLY favorites
        _save_user_state({
            "favoriteKeys": ["hyperliquid:SOL", "hyperliquid:ETH", "hyperliquid:AVAX"],
        })

        state = _get_user_state()
        # Market and terminalLogs remain intact
        self.assertEqual(state["selectedMarket"]["symbol"], "SOL")
        self.assertEqual(state["selectedMarket"]["timeframe"], "4h")
        self.assertEqual(len(state["terminalLogs"]), 2)
        # Favorites updated
        self.assertIn("hyperliquid:AVAX", state["favoriteKeys"])


if __name__ == "__main__":
    unittest.main()

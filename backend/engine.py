"""Deterministic quantitative engine for market context and indicator backtesting."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("backend.engine")


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    if len(df) < 2:
        return pd.Series([0.0] * len(df), index=df.index)

    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.rolling(window=period, min_periods=1).mean()
    return atr


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    if len(df) < period:
        return pd.Series([50.0] * len(df), index=df.index)

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / (avg_loss.replace(0, np.nan))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_market_context(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate factual statistical summary of current market data."""
    if df.empty or len(df) < 5:
        return {
            "error": "Insufficient market data for statistical context",
            "bars": len(df),
        }

    close = df["close"]
    current_price = float(close.iloc[-1])
    first_price = float(close.iloc[0])
    price_change_pct = round(((current_price - first_price) / first_price) * 100.0, 2)

    # Moving averages
    ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1]) if len(df) >= 20 else current_price
    ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(df) >= 50 else current_price
    sma_20 = float(close.rolling(20, min_periods=1).mean().iloc[-1])
    sma_50 = float(close.rolling(50, min_periods=1).mean().iloc[-1])

    # ATR
    atr_series = calculate_atr(df, period=14)
    atr = float(atr_series.iloc[-1])
    atr_pct = round((atr / current_price) * 100.0, 2) if current_price > 0 else 0.0

    # RSI
    rsi_series = calculate_rsi(df, period=14)
    current_rsi = round(float(rsi_series.iloc[-1]), 1)

    # Trend direction & strength
    if current_price > ema_20 > ema_50:
        trend_direction = "bullish"
        trend_strength = "strong" if current_rsi > 55 else "moderate"
    elif current_price < ema_20 < ema_50:
        trend_direction = "bearish"
        trend_strength = "strong" if current_rsi < 45 else "moderate"
    elif current_price > ema_20:
        trend_direction = "mildly_bullish"
        trend_strength = "weak"
    else:
        trend_direction = "mildly_bearish"
        trend_strength = "weak"

    # Volume distribution
    vol = df["volume"]
    vol_last = float(vol.iloc[-1])
    vol_mean_20 = float(vol.rolling(20, min_periods=1).mean().iloc[-1])
    vol_ratio = round(vol_last / vol_mean_20, 2) if vol_mean_20 > 0 else 1.0

    if vol_ratio > 1.5:
        volume_status = "spike"
    elif vol_ratio > 1.1:
        volume_status = "above_average"
    elif vol_ratio < 0.7:
        volume_status = "below_average"
    else:
        volume_status = "normal"

    recent_high = float(df["high"].tail(24).max())
    recent_low = float(df["low"].tail(24).min())

    summary_text = (
        f"Price is at {current_price:.2f} ({price_change_pct:+.2f}% over {len(df)} bars). "
        f"Trend is {trend_direction} ({trend_strength}). EMA20: {ema_20:.2f}, EMA50: {ema_50:.2f}. "
        f"ATR(14) is {atr:.2f} ({atr_pct}% vol). RSI(14) is {current_rsi}. "
        f"Volume ratio is {vol_ratio}x ({volume_status}). Range high: {recent_high:.2f}, low: {recent_low:.2f}."
    )

    return {
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "ema_20": round(ema_20, 2),
        "ema_50": round(ema_50, 2),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "atr_14": round(atr, 2),
        "atr_pct": atr_pct,
        "rsi_14": current_rsi,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "volume_last": round(vol_last, 2),
        "volume_mean_20": round(vol_mean_20, 2),
        "volume_ratio": vol_ratio,
        "volume_status": volume_status,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "bars_analyzed": len(df),
        "summary": summary_text,
    }


def run_quantitative_backtest_logic(df: pd.DataFrame, rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute deterministic quantitative backtest over candle history."""
    if df.empty or len(df) < 30:
        return {
            "error": "Insufficient history for backtesting (minimum 30 bars required)",
            "trades_count": 0,
            "win_rate": 0.0,
            "avg_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "summary": "Ei tarpeeksi kynttilöitä backtestaukseen.",
        }

    rules = rules or {}
    strategy_type = rules.get("type", "ma_crossover").lower()
    fast_period = int(rules.get("fast_period", 20))
    slow_period = int(rules.get("slow_period", 50))
    rsi_period = int(rules.get("rsi_period", 14))
    rsi_oversold = float(rules.get("oversold", 30))
    rsi_overbought = float(rules.get("overbought", 70))

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(close)

    # Compute signals
    buy_signals = np.zeros(n, dtype=bool)
    sell_signals = np.zeros(n, dtype=bool)

    if strategy_type == "rsi":
        rsi = calculate_rsi(df, period=rsi_period).values
        for i in range(1, n):
            if rsi[i - 1] < rsi_oversold and rsi[i] >= rsi_oversold:
                buy_signals[i] = True
            elif rsi[i - 1] > rsi_overbought and rsi[i] <= rsi_overbought:
                sell_signals[i] = True
    elif strategy_type == "breakout":
        lookback = int(rules.get("lookback", 20))
        for i in range(lookback, n):
            if close[i] > np.max(high[i - lookback : i]):
                buy_signals[i] = True
            elif close[i] < np.min(low[i - lookback : i]):
                sell_signals[i] = True
    else:  # default: ma_crossover (EMA or SMA)
        ma_mode = rules.get("ma_mode", "ema").lower()
        if ma_mode == "sma":
            fast_ma = df["close"].rolling(fast_period, min_periods=fast_period).mean().values
            slow_ma = df["close"].rolling(slow_period, min_periods=slow_period).mean().values
        else:
            fast_ma = df["close"].ewm(span=fast_period, adjust=False).mean().values
            slow_ma = df["close"].ewm(span=slow_period, adjust=False).mean().values

        for i in range(1, n):
            if np.isnan(fast_ma[i]) or np.isnan(slow_ma[i]) or np.isnan(fast_ma[i - 1]) or np.isnan(slow_ma[i - 1]):
                continue
            if fast_ma[i - 1] <= slow_ma[i - 1] and fast_ma[i] > slow_ma[i]:
                buy_signals[i] = True
            elif fast_ma[i - 1] >= slow_ma[i - 1] and fast_ma[i] < slow_ma[i]:
                sell_signals[i] = True

    # Simulate position trades
    position = 0  # 0: flat, 1: long
    entry_price = 0.0
    trade_returns: List[float] = []
    equity_curve: List[float] = [1.0]

    for i in range(n):
        current_p = close[i]
        if position == 0 and buy_signals[i]:
            position = 1
            entry_price = current_p
        elif position == 1 and sell_signals[i]:
            ret = (current_p - entry_price) / entry_price
            trade_returns.append(ret)
            equity_curve.append(equity_curve[-1] * (1.0 + ret))
            position = 0
            entry_price = 0.0

    # Close open position at end
    if position == 1 and entry_price > 0:
        ret = (close[-1] - entry_price) / entry_price
        trade_returns.append(ret)
        equity_curve.append(equity_curve[-1] * (1.0 + ret))

    trades_count = len(trade_returns)
    if trades_count == 0:
        return {
            "strategy": strategy_type,
            "trades_count": 0,
            "win_rate": 0.0,
            "avg_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "total_return_pct": 0.0,
            "summary": f"Strategia '{strategy_type}' ei tuottanut yhtään täyttynyttä kauppaa valitussa aikajänteessä.",
        }

    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r <= 0]
    win_rate = round((len(wins) / trades_count) * 100.0, 1)
    avg_return_pct = round(float(np.mean(trade_returns)) * 100.0, 2)
    total_return_pct = round((equity_curve[-1] - 1.0) * 100.0, 2)

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)

    # Max Drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = round(max_dd * 100.0, 2)

    summary_str = (
        f"Kvantitatiivinen backtest ({strategy_type}): {trades_count} kauppaa, "
        f"voittoprosentti {win_rate}%, keskimääräinen tuotto {avg_return_pct:+.2f}%, "
        f"kokonaistuotto {total_return_pct:+.2f}%, profit factor {profit_factor}, "
        f"suurin salkkupudotus (drawdown) {max_drawdown_pct}%."
    )

    return {
        "strategy": strategy_type,
        "trades_count": trades_count,
        "win_rate": win_rate,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "avg_return_pct": avg_return_pct,
        "total_return_pct": total_return_pct,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown_pct,
        "summary": summary_str,
    }


if __name__ == "__main__":
    from data_fetcher import get_candles
    df = get_candles("BTC", "1h", bars=500)
    ctx = calculate_market_context(df)
    print("Market Context Summary:", ctx["summary"])
    bt = run_quantitative_backtest_logic(df, {"type": "ma_crossover", "fast_period": 20, "slow_period": 50})
    print("Backtest Result:", bt["summary"])

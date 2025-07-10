"""EMA 20/100 crossover strategy (Run-the-Trend).

Entry LONG when EMA20 crosses above EMA100 on the last closed candle.
Entry SHORT when EMA20 crosses below EMA100.
Trailing stop initial distance = min(4% of price, 2.5 * ATR20).
"""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_ema
from strategies.base import BaseStrategy


class EMA20_100(BaseStrategy):
    name = "EMA20_100"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        # Need at least 101 candles
        if len(df) < 101:
            return Signal("flat")

        close = df["Close"]
        ema20 = compute_ema(close, 20)
        ema100 = compute_ema(close, 100)
        diff = ema20 - ema100

        # Use last two closed candles to detect new crossing
        prev = diff.iloc[-2]
        curr = diff.iloc[-1]

        action = "flat"
        if prev < 0 < curr:
            action = "long"
        elif prev > 0 > curr:
            action = "short"

        if action == "flat":
            return Signal("flat")

        atr20 = extras.get("ATR_20")
        if atr20 is None or pd.isna(atr20.iloc[-1]):
            return Signal("flat")

        price = float(close.iloc[-1])
        stop_dist = min(0.04 * price, 2.5 * float(atr20.iloc[-1]))
        return Signal(action, stop_distance=stop_dist)

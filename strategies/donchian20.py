"""Donchian 20 Breakout strategy.

Simplified MVP implementation: generates LONG when last close > 20-period high;
SHORT when < 20-period low. Trailing stop distance = 2 * ATR20.
"""
from __future__ import annotations

import pandas as pd

from core.utils import Signal
from strategies.base import BaseStrategy


class Donchian20(BaseStrategy):
    name = "Donchian20"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 21:
            return Signal("flat")

        high20 = df["High"].rolling(window=20).max()
        low20 = df["Low"].rolling(window=20).min()
        close = df["Close"]

        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]

        action = "flat"
        if prev_close <= high20.iloc[-2] and last_close > high20.iloc[-1]:
            action = "long"
        elif prev_close >= low20.iloc[-2] and last_close < low20.iloc[-1]:
            action = "short"
        else:
            return Signal("flat")

        atr20 = extras.get("ATR_20")
        if atr20 is None:
            return Signal("flat")
        stop_dist = 2.0 * float(atr20.iloc[-1])
        return Signal(action, stop_distance=stop_dist)

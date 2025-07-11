"""MACD Zero-Cross Boost strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_macd
from strategies.base import BaseStrategy


class MACDZeroCross(BaseStrategy):
    name = "MACDZeroCross"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 35:
            return Signal("flat")
        _, _, hist = compute_macd(df["Close"])
        prev = hist.iloc[-2]
        curr = hist.iloc[-1]
        action = "flat"
        if prev < 0 <= curr:
            action = "long"
        elif prev > 0 >= curr:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

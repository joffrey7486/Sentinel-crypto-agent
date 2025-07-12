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
        macd, signal, hist = compute_macd(df["Close"])
        prev_hist = hist.iloc[-2]
        curr_hist = hist.iloc[-1]
        curr_macd = macd.iloc[-1]
        curr_signal = signal.iloc[-1]

        action = "flat"
        if (
            prev_hist < 0 <= curr_hist
            and curr_hist > prev_hist
            and curr_macd > curr_signal
        ):
            action = "long"
        elif (
            prev_hist > 0 >= curr_hist
            and curr_hist < prev_hist
            and curr_macd < curr_signal
        ):
            action = "short"

        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = 2.0 * float(atr14.iloc[-1])

        return Signal(action, stop_distance=stop)

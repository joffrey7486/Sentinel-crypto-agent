"""Keltner Channel Upper-Ride strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_keltner_channels
from strategies.base import BaseStrategy


class KeltnerUpperRide(BaseStrategy):
    name = "KeltnerUpperRide"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 21:
            return Signal("flat")
        middle, upper, _ = compute_keltner_channels(df)
        close = df["Close"]
        prev_close = close.iloc[-2]
        curr_close = close.iloc[-1]
        prev_above = prev_close > upper.iloc[-2]
        curr_above = curr_close > upper.iloc[-1]
        action = "flat"
        if not prev_above and curr_above:
            action = "long"
        elif prev_above and curr_close < middle.iloc[-1]:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = 1.5 * float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

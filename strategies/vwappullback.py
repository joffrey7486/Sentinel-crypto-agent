"""VWAP Pullback Bounce strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_vwap
from strategies.base import BaseStrategy


class VWAPPullback(BaseStrategy):
    name = "VWAPPullback"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 2:
            return Signal("flat")
        vwap = compute_vwap(df)
        close = df["Close"]
        prev_close = close.iloc[-2]
        curr_close = close.iloc[-1]
        prev_above = prev_close > vwap.iloc[-2]
        curr_above = curr_close > vwap.iloc[-1]
        action = "flat"
        if not prev_above and curr_above:
            action = "long"
        elif prev_above and not curr_above:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

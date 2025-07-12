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
        open_ = df["Open"]

        prev_close = close.iloc[-2]
        curr_close = close.iloc[-1]
        prev_above = prev_close > vwap.iloc[-2]
        curr_above = curr_close > vwap.iloc[-1]
        is_green = curr_close > open_.iloc[-1]

        action = "flat"
        if not prev_above and curr_above and is_green:
            action = "long"
        elif prev_above and not curr_above and not is_green:
            action = "short"

        price = float(curr_close)
        stop = 0.008 * price
        return Signal(action, stop_distance=stop)

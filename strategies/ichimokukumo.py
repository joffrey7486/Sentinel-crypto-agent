"""Ichimoku Kumo-Flip strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_ichimoku
from strategies.base import BaseStrategy


class IchimokuKumo(BaseStrategy):
    name = "IchimokuKumo"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 60:
            return Signal("flat")
        ich = compute_ichimoku(df)
        close = df["Close"]
        prev_in_cloud = ich["span_a"].iloc[-2] < close.iloc[-2] < ich["span_b"].iloc[-2] or ich["span_b"].iloc[-2] < close.iloc[-2] < ich["span_a"].iloc[-2]
        curr_above = close.iloc[-1] > max(ich["span_a"].iloc[-1], ich["span_b"].iloc[-1])
        curr_below = close.iloc[-1] < min(ich["span_a"].iloc[-1], ich["span_b"].iloc[-1])
        action = "flat"
        if prev_in_cloud and curr_above:
            action = "long"
        elif prev_in_cloud and curr_below:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = 1.5 * float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

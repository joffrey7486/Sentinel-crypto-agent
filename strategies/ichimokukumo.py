"""Ichimoku Kumo-Flip strategy.

Entry when price exits the cloud with the Chikou span above price 26 periods
ago. The initial stop is ``3 * ATR20`` and trailing follows ``max(stop, Kijun +
0.5 * ATR)``.
"""
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
        prev_in_cloud = (
            ich["span_a"].iloc[-2] < close.iloc[-2] < ich["span_b"].iloc[-2]
            or ich["span_b"].iloc[-2] < close.iloc[-2] < ich["span_a"].iloc[-2]
        )
        curr_above = close.iloc[-1] > max(
            ich["span_a"].iloc[-1], ich["span_b"].iloc[-1]
        )
        curr_below = close.iloc[-1] < min(
            ich["span_a"].iloc[-1], ich["span_b"].iloc[-1]
        )
        chikou_ok = False
        if len(df) > 26:
            chikou_ok = close.iloc[-1] > close.shift(26).iloc[-1]

        action = "flat"
        if prev_in_cloud and curr_above and chikou_ok:
            action = "long"
        elif prev_in_cloud and curr_below and chikou_ok:
            action = "short"

        atr20 = extras.get("ATR_20")
        stop = None
        if atr20 is not None:
            stop = 3.0 * float(atr20.iloc[-1])

        return Signal(action, stop_distance=stop, trailing_mode="kijun")

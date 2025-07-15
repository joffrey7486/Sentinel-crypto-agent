"""Bollinger Squeeze Break strategy.

Entry is triggered when price exits a Bollinger Band squeeze and the
Bollinger Band width relative to price is below 2%. The resulting
position uses a trailing stop of ``1.8 * ATR14``.
"""
from __future__ import annotations

import pandas as pd

from core.utils import (
    Signal,
    compute_bollinger_bands,
    compute_keltner_channels,
)
from strategies.base import BaseStrategy


class BollingerSqueeze(BaseStrategy):
    name = "BollingerSqueeze"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 21:
            return Signal("flat")

        close = df["Close"]
        _, bb_upper, bb_lower = compute_bollinger_bands(close)
        _, kc_upper, kc_lower = compute_keltner_channels(df)

        width_bb = bb_upper - bb_lower
        width_kc = kc_upper - kc_lower

        prev_squeeze = width_bb.iloc[-2] < width_kc.iloc[-2]
        squeeze = width_bb.iloc[-1] < width_kc.iloc[-1]
        width_ratio = width_bb.iloc[-1] / close.iloc[-1]
        action = "flat"
        if prev_squeeze and not squeeze and width_ratio < 0.02:
            if close.iloc[-1] > bb_upper.iloc[-1]:
                action = "long"
            elif close.iloc[-1] < bb_lower.iloc[-1]:
                action = "short"

        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = 1.8 * float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

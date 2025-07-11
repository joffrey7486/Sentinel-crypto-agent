"""Parabolic SAR Flip-Trend strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_psar
from strategies.base import BaseStrategy


class SARFlip(BaseStrategy):
    name = "SARFlip"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 3:
            return Signal("flat")
        psar = compute_psar(df)
        close = df["Close"]
        prev_above = close.iloc[-2] > psar.iloc[-2]
        curr_above = close.iloc[-1] > psar.iloc[-1]
        action = "flat"
        if not prev_above and curr_above:
            action = "long"
        elif prev_above and not curr_above:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = 2.0 * float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

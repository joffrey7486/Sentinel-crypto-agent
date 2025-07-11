"""RSI Divergence strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_rsi
from strategies.base import BaseStrategy


class RSIDivergence(BaseStrategy):
    name = "RSIDivergence"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 30:
            return Signal("flat")
        rsi = compute_rsi(df["Close"])
        prev = rsi.iloc[-2]
        curr = rsi.iloc[-1]
        action = "flat"
        if prev < 30 <= curr:
            action = "long"
        elif prev > 70 >= curr:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

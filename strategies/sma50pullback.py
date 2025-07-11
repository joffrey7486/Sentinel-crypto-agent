"""SMA 50 Pullback Engulf strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_sma
from strategies.base import BaseStrategy


class SMA50Pullback(BaseStrategy):
    name = "SMA50Pullback"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 51:
            return Signal("flat")
        sma = compute_sma(df["Close"], 50)
        prev_close = df["Close"].iloc[-2]
        curr_close = df["Close"].iloc[-1]
        prev_above = prev_close > sma.iloc[-2]
        curr_above = curr_close > sma.iloc[-1]
        action = "flat"
        if prev_above and curr_close <= sma.iloc[-1] * 1.002:
            action = "long"
        elif not prev_above and curr_close >= sma.iloc[-1] * 0.998:
            action = "short"
        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

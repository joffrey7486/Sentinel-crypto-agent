"""RSI Divergence strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_rsi
from strategies.base import BaseStrategy


class RSIDivergence(BaseStrategy):
    name = "RSIDivergence"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        if len(df) < 5:
            return Signal("flat")

        rsi = compute_rsi(df["Close"])
        action = "flat"

        # Use the last closed candle (-2) and one a few candles back (-4)
        rsi_curr = rsi.iloc[-2]
        rsi_prev = rsi.iloc[-4]
        low_curr = df["Low"].iloc[-2]
        low_prev = df["Low"].iloc[-4]
        high_curr = df["High"].iloc[-2]
        high_prev = df["High"].iloc[-4]

        if rsi_curr < 30:
            # Price makes a lower low but RSI a higher low -> bullish divergence
            if low_curr < low_prev and rsi_curr > rsi_prev:
                action = "long"
            # Price makes a higher high but RSI a lower high -> bearish divergence
            elif high_curr > high_prev and rsi_curr < rsi_prev:
                action = "short"

        atr14 = extras.get("ATR_14")
        stop = None
        if atr14 is not None:
            stop = float(atr14.iloc[-1])
        return Signal(action, stop_distance=stop)

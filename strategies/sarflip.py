"""Parabolic SAR Flip-Trend strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal, compute_psar
from strategies.base import BaseStrategy


class SARFlip(BaseStrategy):
    name = "SARFlip"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        # Need sufficient history for volume comparison (2 days of 4h candles)
        if len(df) < 12:
            return Signal("flat")

        volume = df["Volume"]
        curr_vol = volume.iloc[-6:].sum()
        prev_vol = volume.iloc[-12:-6].sum()
        if prev_vol <= 0:
            return Signal("flat")
        vol_move = abs(curr_vol - prev_vol) / prev_vol * 100.0
        if vol_move <= 2:
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
            psar_dist = abs(close.iloc[-1] - psar.iloc[-1])
            atr_dist = 1.6 * float(atr14.iloc[-1])
            stop = max(psar_dist, atr_dist)
        return Signal(action, stop_distance=stop)

"""Placeholder MACD Zero-Cross Boost strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal
from strategies.base import BaseStrategy


class MACDZeroCross(BaseStrategy):
    name = "MACDZeroCross"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        return Signal("flat")

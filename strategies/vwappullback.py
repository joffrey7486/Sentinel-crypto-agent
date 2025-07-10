"""Placeholder VWAP Pullback Bounce strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal
from strategies.base import BaseStrategy


class VWAPPullback(BaseStrategy):
    name = "VWAPPullback"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        return Signal("flat")

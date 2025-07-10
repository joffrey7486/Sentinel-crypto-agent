"""Placeholder Bollinger Squeeze Break strategy for MVP.
Returns flat until full logic implemented.
"""
from __future__ import annotations

import pandas as pd

from core.utils import Signal
from strategies.base import BaseStrategy


class BollingerSqueeze(BaseStrategy):
    name = "BollingerSqueeze"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        return Signal("flat")

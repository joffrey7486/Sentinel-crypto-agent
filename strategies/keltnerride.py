"""Placeholder Keltner Channel Upper-Ride strategy."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal
from strategies.base import BaseStrategy


class KeltnerUpperRide(BaseStrategy):
    name = "KeltnerUpperRide"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):  # type: ignore
        return Signal("flat")

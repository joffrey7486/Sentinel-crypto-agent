"""Base strategy class with helper to get last finished candle index etc."""
from __future__ import annotations

import pandas as pd

from core.utils import Signal


class BaseStrategy:
    name: str = "base"

    @classmethod
    def last_candle(cls, df: pd.DataFrame) -> pd.Series:
        """Return the last *closed* candle (second to last row)."""
        return df.iloc[-2]

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]) -> Signal:  # type: ignore
        raise NotImplementedError

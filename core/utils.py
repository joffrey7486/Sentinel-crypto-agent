"""Utility functions for Sentinel Crypto Agent core module."""
from __future__ import annotations

import pandas as pd
import numpy as np


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Compute Exponential Moving Average (EMA) for a pandas Series."""
    return series.ewm(span=period, adjust=False).mean()


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range (ATR) using simple moving average of True Range.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: High, Low, Close
    period : int, optional
        Lookback period for ATR, by default 14

    Returns
    -------
    pd.Series
        ATR values with same index as df
    """
    high = df['High']
    low = df['Low']
    close = df['Close']

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.rolling(window=period, min_periods=1).mean()  # simple (non Wilder smoothing)
    return atr


def compute_true_range(df: pd.DataFrame) -> pd.Series:
    """Compute True Range (TR)."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def percent_distance(a: float, b: float) -> float:
    """Return percentage distance between two prices."""
    return (a - b) / b * 100.0


class Signal:
    """Standard signal object returned by generate_signal()."""

    def __init__(self, action: str, stop_distance: float | None = None):
        if action not in {"long", "short", "flat"}:
            raise ValueError("action must be 'long', 'short', or 'flat'")
        self.action = action
        self.stop_distance = stop_distance  # absolute distance from price

    def __repr__(self) -> str:  # pragma: no cover
        return f"Signal(action={self.action}, stop_distance={self.stop_distance})"

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


def compute_sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=1).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price."""
    price = (df['High'] + df['Low'] + df['Close']) / 3
    cum_vol = df['Volume'].cumsum()
    cum_vol_price = (price * df['Volume']).cumsum()
    return cum_vol_price / cum_vol


def compute_bollinger_bands(series: pd.Series, period: int = 20, width: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return middle, upper and lower Bollinger Bands."""
    sma = compute_sma(series, period)
    std = series.rolling(window=period, min_periods=1).std()
    upper = sma + width * std
    lower = sma - width * std
    return sma, upper, lower


def compute_keltner_channels(df: pd.DataFrame, period: int = 20, width: float = 1.5) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return middle, upper and lower Keltner Channels."""
    ema = compute_ema((df['High'] + df['Low'] + df['Close']) / 3, period)
    atr = compute_atr(df, period)
    upper = ema + width * atr
    lower = ema - width * atr
    return ema, upper, lower


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line and histogram."""
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = compute_ema(macd, signal)
    hist = macd - macd_signal
    return macd, macd_signal, hist


def compute_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """Return Ichimoku components as a DataFrame."""
    high = df['High']
    low = df['Low']
    tenkan_sen = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun_sen = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    return pd.DataFrame({
        'tenkan': tenkan_sen,
        'kijun': kijun_sen,
        'span_a': span_a,
        'span_b': span_b,
    })


def compute_psar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """Compute Parabolic SAR."""
    high = df['High']
    low = df['Low']
    psar = pd.Series(index=df.index, dtype=float)
    bull = True
    af = step
    ep = high.iloc[0]
    psar.iloc[0] = low.iloc[0]
    for i in range(1, len(df)):
        prev_psar = psar.iloc[i-1]
        if bull:
            psar.iloc[i] = prev_psar + af * (ep - prev_psar)
            if i >= 2:
                psar.iloc[i] = min(psar.iloc[i], low.iloc[i-1], low.iloc[i-2])
            if low.iloc[i] < psar.iloc[i]:
                bull = False
                psar.iloc[i] = ep
                af = step
                ep = low.iloc[i]
        else:
            psar.iloc[i] = prev_psar + af * (ep - prev_psar)
            if i >= 2:
                psar.iloc[i] = max(psar.iloc[i], high.iloc[i-1], high.iloc[i-2])
            if high.iloc[i] > psar.iloc[i]:
                bull = True
                psar.iloc[i] = ep
                af = step
                ep = high.iloc[i]
        if bull:
            if high.iloc[i] > ep:
                ep = high.iloc[i]
                af = min(af + step, max_step)
        else:
            if low.iloc[i] < ep:
                ep = low.iloc[i]
                af = min(af + step, max_step)
    return psar


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

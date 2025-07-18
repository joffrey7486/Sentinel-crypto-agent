import pandas as pd
import numpy as np
from core.utils import (
    compute_ema,
    compute_true_range,
    compute_atr,
    compute_macd,
)


def test_compute_ema():
    series = pd.Series([1, 2, 3, 4, 5])
    result = compute_ema(series, 3)
    expected = series.ewm(span=3, adjust=False).mean()
    pd.testing.assert_series_equal(result, expected)


def test_true_range_and_atr(sample_ohlcv):
    tr = compute_true_range(sample_ohlcv)
    expected_tr = pd.concat([
        sample_ohlcv['High'] - sample_ohlcv['Low'],
        (sample_ohlcv['High'] - sample_ohlcv['Close'].shift(1)).abs(),
        (sample_ohlcv['Low'] - sample_ohlcv['Close'].shift(1)).abs(),
    ], axis=1).max(axis=1)
    pd.testing.assert_series_equal(tr, expected_tr)

    atr = compute_atr(sample_ohlcv, 14)
    expected_atr = expected_tr.rolling(window=14, min_periods=1).mean()
    pd.testing.assert_series_equal(atr, expected_atr)


def test_compute_macd():
    series = pd.Series(np.linspace(1, 10, 50))
    macd, signal, hist = compute_macd(series)
    ema_fast = series.ewm(span=12, adjust=False).mean()
    ema_slow = series.ewm(span=26, adjust=False).mean()
    exp_macd = ema_fast - ema_slow
    exp_signal = exp_macd.ewm(span=9, adjust=False).mean()
    pd.testing.assert_series_equal(macd, exp_macd)
    pd.testing.assert_series_equal(signal, exp_signal)
    pd.testing.assert_series_equal(hist, exp_macd - exp_signal)

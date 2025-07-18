import site
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Ensure project root is on the Python path for imports
site.addsitedir(str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def sample_ohlcv():
    index = pd.date_range("2021-01-01", periods=120, freq="H", tz="UTC")
    # Use a strong rally on the last three candles so EMA20 slope is
    # positive and crosses above EMA100
    close = pd.Series([100]*100 + [50]*17 + [60, 300, 400], index=index)
    df = pd.DataFrame({
        "Open": close,
        "High": close + 1,
        "Low": close - 1,
        "Close": close,
        "Volume": np.random.randint(100, 200, size=len(close))
    }, index=index)
    return df

@pytest.fixture
def donchian_df():
    # At least 200 candles so Donchian20 can produce a valid signal. We
    # create a simple upward trend where the last close breaks above the
    # 20-period high and is also above the SMA200.
    index = pd.date_range("2021-02-01", periods=201, freq="H", tz="UTC")
    high = pd.Series(range(1, 202), index=index)
    low = high - 1
    close = pd.Series(high - 0.5, index=index)
    close.iloc[-1] = high.iloc[-1] + 1  # breakout on the last candle
    df = pd.DataFrame({
        "Open": low,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": np.random.randint(100, 200, size=len(close))
    }, index=index)
    return df

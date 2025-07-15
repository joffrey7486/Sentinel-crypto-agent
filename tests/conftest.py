import pandas as pd
import numpy as np
import pytest

@pytest.fixture
def sample_ohlcv():
    index = pd.date_range("2021-01-01", periods=120, freq="H", tz="UTC")
    close = pd.Series([100]*100 + [50]*18 + [300, 400], index=index)
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
    index = pd.date_range("2021-02-01", periods=21, freq="H", tz="UTC")
    high = pd.Series(list(range(1,21)) + [22], index=index)
    low = high - 1
    close = pd.Series(list(high[:-1] - 0.5) + [23], index=index)
    df = pd.DataFrame({
        "Open": low,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": np.random.randint(100, 200, size=len(close))
    }, index=index)
    return df

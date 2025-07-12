import pandas as pd
import numpy as np

from strategies.sarflip import SARFlip
from core.utils import compute_psar


def _make_df(volumes):
    idx = pd.date_range("2024-01-01", periods=len(volumes), freq="4H")
    data = {
        "Open": np.arange(len(volumes), dtype=float),
        "High": np.arange(len(volumes), dtype=float) + 1,
        "Low": np.arange(len(volumes), dtype=float),
        "Close": np.arange(len(volumes), dtype=float) + 0.5,
        "Volume": volumes,
    }
    return pd.DataFrame(data, index=idx)


def test_volume_filter_blocks_signal():
    df = _make_df([100] * 12)
    extras = {"ATR_14": pd.Series([0.1] * 12, index=df.index)}
    sig = SARFlip.generate_signal(df, extras)
    assert sig.action == "flat"
    assert sig.stop_distance is None


def test_stop_distance_uses_max_of_psar_or_atr():
    volumes = [100] * 6 + [130] * 6
    df = _make_df(volumes)
    atr = pd.Series([0.1] * len(df), index=df.index)
    extras = {"ATR_14": atr}
    sig = SARFlip.generate_signal(df, extras)
    psar = compute_psar(df)
    expected = max(abs(df["Close"].iloc[-1] - psar.iloc[-1]), 1.6 * atr.iloc[-1])
    assert sig.stop_distance == expected


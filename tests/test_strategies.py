from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.utils import compute_atr
from strategies.ema20_100 import EMA20_100
from strategies.donchian20 import Donchian20


def test_ema20_100_long_signal(sample_ohlcv):
    extras = {"ATR_20": compute_atr(sample_ohlcv, 20)}
    signal = EMA20_100.generate_signal(sample_ohlcv, extras)
    assert signal.action == "long"
    assert signal.stop_distance is not None and signal.stop_distance > 0


def test_donchian20_long_signal(donchian_df):
    extras = {"ATR_20": compute_atr(donchian_df, 20)}
    signal = Donchian20.generate_signal(donchian_df, extras)
    assert signal.action == "long"
    assert signal.stop_distance is not None and signal.stop_distance > 0

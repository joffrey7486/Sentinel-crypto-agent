import pandas as pd
import strategies.macdzerocross as macdzerocross


def test_macdzerocross_long(monkeypatch):
    df = pd.DataFrame({'Close': [1] * 35})

    def fake_macd(series):
        macd = pd.Series([0] * 33 + [0.3, 1.0])
        signal = pd.Series([0] * 33 + [0.4, 0.8])
        hist = macd - signal
        return macd, signal, hist

    monkeypatch.setattr(macdzerocross, "compute_macd", fake_macd)
    extras = {"ATR_14": pd.Series([1] * 35)}
    sig = macdzerocross.MACDZeroCross.generate_signal(df, extras)
    assert sig.action == "long"
    assert sig.stop_distance == 2.0


def test_macdzerocross_short(monkeypatch):
    df = pd.DataFrame({'Close': [1] * 35})

    def fake_macd(series):
        macd = pd.Series([0] * 33 + [1.0, 0.2])
        signal = pd.Series([0] * 33 + [0.8, 0.5])
        hist = macd - signal
        return macd, signal, hist

    monkeypatch.setattr(macdzerocross, "compute_macd", fake_macd)
    extras = {"ATR_14": pd.Series([1] * 35)}
    sig = macdzerocross.MACDZeroCross.generate_signal(df, extras)
    assert sig.action == "short"
    assert sig.stop_distance == 2.0

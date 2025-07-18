import pandas as pd
from core.engine import Engine


def _dummy_exchange():
    class Ex:
        def load_markets(self):
            pass
        def fetch_balance(self):
            return {"USDC": {"total": 1000}}
        def fetch_ticker(self, symbol):
            return {"quoteVolume": 1_000_000}
        def create_order(self, symbol, order_type, side, amount):
            return {"side": side, "amount": amount}
    return Ex()


def test_trailing_stop_never_decreases_long(monkeypatch):
    monkeypatch.setattr("ccxt.binance", lambda params=None: _dummy_exchange())
    eng = Engine(paper=True)
    df = pd.DataFrame(
        {
            "Open": [1, 2, 3],
            "High": [1.5, 2.5, 2.0],
            "Low": [0.5, 1.5, 1.0],
            "Close": [1, 2, 1.8],
            "Volume": [1, 1, 1],
        },
        index=pd.date_range("2024-01-01", periods=3, freq="4H", tz="UTC"),
    )
    eng.positions = [
        {
            "time": str(df.index[-2]),
            "symbol": "BTC/USDC",
            "side": "long",
            "amount": 1.0,
            "price": 2.0,
            "order": {},
            "status": "open",
            "stop_price": 1.0,
            "atr_multiplier": 2.0,
            "armed": True,
            "trail_mode": "atr",
            "strategy": "test",
            "stop_pct": 50.0,
            "signal_source": "test",
        }
    ]
    extras = {"ATR_20": pd.Series([1, 1, 1], index=df.index)}
    eng._update_open_positions(df, extras)
    assert eng.positions[0]["stop_price"] >= 1.0


def test_trailing_stop_never_increases_short(monkeypatch):
    monkeypatch.setattr("ccxt.binance", lambda params=None: _dummy_exchange())
    eng = Engine(paper=True)
    df = pd.DataFrame(
        {
            "Open": [3, 2, 1],
            "High": [3.5, 2.5, 1.5],
            "Low": [2.5, 1.5, 0.5],
            "Close": [3, 2, 1.2],
            "Volume": [1, 1, 1],
        },
        index=pd.date_range("2024-01-01", periods=3, freq="4H", tz="UTC"),
    )
    eng.positions = [
        {
            "time": str(df.index[-2]),
            "symbol": "BTC/USDC",
            "side": "short",
            "amount": 1.0,
            "price": 2.0,
            "order": {},
            "status": "open",
            "stop_price": 3.0,
            "atr_multiplier": 2.0,
            "armed": True,
            "trail_mode": "atr",
            "strategy": "test",
            "stop_pct": 50.0,
            "signal_source": "test",
        }
    ]
    extras = {"ATR_20": pd.Series([1, 1, 1], index=df.index)}
    eng._update_open_positions(df, extras)
    assert eng.positions[0]["stop_price"] <= 3.0

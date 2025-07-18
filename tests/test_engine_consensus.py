import types
from core.engine import Engine, StrategyBase
from core.utils import Signal

class DummyExchange:
    def load_markets(self):
        pass
    def fetch_balance(self):
        return {"USDC": {"total": 1000}}
    def fetch_ticker(self, symbol):
        return {"quoteVolume": 1_000_000}
    def create_order(self, symbol, order_type, side, amount):
        return {"side": side, "amount": amount}

class StratA(StrategyBase):
    name = "EMA20_100"
    @classmethod
    def generate_signal(cls, df, extras):
        return Signal("long", stop_distance=1)

class StratB(StrategyBase):
    name = "Donchian20"
    @classmethod
    def generate_signal(cls, df, extras):
        return Signal("long", stop_distance=1)

class StratC(StrategyBase):
    name = "Other"
    @classmethod
    def generate_signal(cls, df, extras):
        return Signal("long", stop_distance=1)


def test_engine_consensus_long(sample_ohlcv, monkeypatch):
    # patch ccxt factory
    monkeypatch.setattr("ccxt.binance", lambda params=None: DummyExchange())
    engine = Engine()
    engine.register_strategy(StratA)
    engine.register_strategy(StratB)
    engine.register_strategy(StratC)

    orders = []
    def fake_send_order(self, symbol, side, amount, price, stop_distance, atr_value, trailing_mode=None, strategy=None):
        orders.append((side, amount))
    monkeypatch.setattr(Engine, "_send_order", fake_send_order)
    monkeypatch.setattr(engine.risk_manager, "allows_new_position", lambda *a, **k: (True, 1))

    engine.run_once("BTC/USDC", df=sample_ohlcv)
    assert orders and orders[0][0] == "long"

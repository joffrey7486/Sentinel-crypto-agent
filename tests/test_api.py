from fastapi.testclient import TestClient
import webview
import ccxt
from core.engine import Engine
from core.api import init_api, app

class DummyExchange:
    def load_markets(self):
        pass
    def fetch_balance(self):
        return {"USDC": {"total": 1000}}
    def fetch_ticker(self, symbol):
        return {"quoteVolume": 1_000_000}
    def create_order(self, symbol, order_type, side, amount):
        return {"side": side, "amount": amount}


def test_status_endpoint(monkeypatch):
    monkeypatch.setattr("ccxt.binance", lambda params=None: DummyExchange())
    eng = Engine()
    init_api(eng)
    client = TestClient(app)
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["alive"] is True


def test_webview_smoke():
    w = webview.create_window("Test", html="<html></html>", hidden=True)
    assert w.title == "Test"


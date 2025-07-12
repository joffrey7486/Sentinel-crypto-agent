"""Main trading signal engine for Sentinel Crypto Agent.

This module fetches OHLCV data every 4h, computes indicators once, and asks each
registered strategy for a signal. It then decides whether to act, respecting the
instrument-lock and logs the decision.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Type
import os
import json

import ccxt
import pandas as pd
import yaml

from .utils import Signal

logger = logging.getLogger("sentinel.engine")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class StrategyBase:
    name: str = "base"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: Dict[str, pd.Series]) -> Signal:  # noqa: D401  # type: ignore
        """Return trading signal for the last closed candle."""
        raise NotImplementedError


class Engine:
    def __init__(
        self,
        config_path: Path = Path("config.yaml"),
        exchange_id: str = "binance",
        timeframe: str = "4h",
    ) -> None:
        self.config = self._load_config(config_path)
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        self.exchange = getattr(ccxt, exchange_id)({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        self.exchange.load_markets()
        self.timeframe = timeframe
        self.strategies: List[Type[StrategyBase]] = []
        self.instrument_lock: Dict[str, str] = {}  # pair -> strategy_name
        self.positions_path = Path("positions.json")
        self.positions: List[Dict[str, str]] = self._load_positions()

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        return config

    def register_strategy(self, strategy_cls: Type[StrategyBase]) -> None:
        self.strategies.append(strategy_cls)

    def _load_positions(self) -> List[Dict[str, str]]:
        if self.positions_path.exists():
            with open(self.positions_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return []

    def _save_positions(self) -> None:
        with open(self.positions_path, "w", encoding="utf-8") as fh:
            json.dump(self.positions, fh, indent=2)

    def _send_order(self, symbol: str, side: str, price: float) -> None:
        """Send a market order to the exchange and persist it.

        Parameters
        ----------
        symbol: str
            Trading pair (e.g. ``"BTC/USDC"``).
        side: str
            Desired position direction from the strategy, ``"long"`` or ``"short"``.
            It is converted to ``"buy"``/``"sell"`` for the exchange API.
        price: float
            Current market price used to size the position.
        """

        size_pct = float(self.config.get("position_size_pct", 0.01))
        balance = self.exchange.fetch_balance()
        base = symbol.split("/")[0]
        quote = symbol.split("/")[1]
        avail = balance.get(quote, {}).get("free")
        if avail:
            amount = (avail * size_pct) / price
        else:
            amount = 0

        if not amount:
            logger.warning("Skipping order for %s, computed amount is %s", symbol, amount)
            return

        # CCXT expects 'buy' or 'sell'; map our signal sides accordingly
        order_side = "buy" if side == "long" else "sell"

        try:
            order = self.exchange.create_order(symbol, "market", order_side, amount)
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Order failed: %s", exc)
            order = {"error": str(exc)}
        self.positions.append({
            "time": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "order": order,
        })

    def fetch_ohlcv(self, symbol: str, limit: int = 2000) -> pd.DataFrame:
        logger.info("Fetching OHLCV for %s", symbol)
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms", utc=True)
        return df.set_index("Timestamp")

    def run_once(self, symbol: str, df: Optional[pd.DataFrame] = None) -> None:
        if df is None:
            df = self.fetch_ohlcv(symbol)

        # compute shared indicators
        extras = {}
        # Example: compute ATR 20 for all strategies needing it
        from .utils import compute_atr

        extras["ATR_20"] = compute_atr(df, 20)
        extras["ATR_14"] = compute_atr(df, 14)

        last_candle = df.iloc[-1]
        price = float(last_candle["Close"])
        time = last_candle.name.tz_convert(timezone.utc)

        for strat_cls in self.strategies:
            # skip if instrument locked by another strategy
            if symbol in self.instrument_lock and self.instrument_lock[symbol] != strat_cls.name:
                continue
            signal = strat_cls.generate_signal(df, extras)
            if signal.action == "flat":
                continue
            logger.info(
                "%s %s -> %s stop_distance=%.4f",
                time,
                symbol,
                signal.action.upper(),
                signal.stop_distance or 0.0,
            )
            self.instrument_lock[symbol] = strat_cls.name
            self._send_order(symbol, signal.action, price)
            self._save_positions()
            break  # Only first strategy acts this tick.


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True, help="Symbol pair like BTC/USDC")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    eng = Engine()
    # TODO: register strategy classes
    # from strategies.ema20_100 import EMA20_100
    # eng.register_strategy(EMA20_100)

    if args.once:
        eng.run_once(args.pair)
    else:
        # Simplistic loop every 4h
        while True:
            now = datetime.now(timezone.utc)
            if now.hour % 4 == 0 and now.minute < 2:
                eng.run_once(args.pair)
            time.sleep(60)

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

from .risk_manager import RiskManager
from .utils import Signal

logger = logging.getLogger("sentinel.engine")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class StrategyBase:
    name: str = "base"

    @classmethod
    def generate_signal(
        cls, df: pd.DataFrame, extras: Dict[str, pd.Series]
    ) -> Signal:  # noqa: D401  # type: ignore
        """Return trading signal for the last closed candle."""
        raise NotImplementedError


class Engine:
    def __init__(
        self,
        config_path: Path = Path("config.yaml"),
        exchange_id: str = "binance",
        timeframe: str = "4h",
        paper: bool = False,
    ) -> None:
        self.config = self._load_config(config_path)
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        self.exchange = getattr(ccxt, exchange_id)(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )
        self.exchange.load_markets()
        self.timeframe = timeframe
        self.paper = paper
        self.strategies: List[Type[StrategyBase]] = []
        self.instrument_lock: Dict[str, str] = {}  # pair -> strategy_name
        self.positions_path = Path("positions.json")
        self.positions: List[Dict[str, str]] = self._load_positions()

        self.delta_be = float(self.config.get("delta_be", 0.0015))

        # Risk manager loads risk.yml for thresholds
        self.risk_manager = RiskManager()
        try:
            bal = self.exchange.fetch_balance()
            usdc = bal.get("USDC", {}).get("total") or 0
        except Exception:  # pragma: no cover - network errors
            usdc = 0
        self.risk_manager.equity = float(usdc)
        self.risk_manager.equity_high = self.risk_manager.equity
        self.risk_manager.daily_start_equity = self.risk_manager.equity

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            default_config = {
                "default_pair": "BTC/USDC",
                "exchange": "binance",
                "strategies": [
                    "EMA20_100",
                    "Donchian20",
                    "BollingerSqueeze",
                    "IchimokuKumo",
                    "MACDZeroCross",
                    "VWAPPullback",
                    "KeltnerUpperRide",
                    "SMA50Pullback",
                    "SARFlip",
                    "RSIDivergence",
                ],
                "fees": 0.0005,
                "slippage": 0.0005,
                "position_size_pct": 0.01,
                "delta_be": 0.0015,
            }
            with open(path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(default_config, fh)
            return default_config
        with open(path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
        return config

    def register_strategy(self, strategy_cls: Type[StrategyBase]) -> None:
        self.strategies.append(strategy_cls)

    def _get_open_position(self, symbol: str) -> Optional[Dict[str, str]]:
        """Return the last open position for the given symbol, if any."""
        for pos in reversed(self.positions):
            if pos.get("symbol") == symbol and pos.get("status") == "open":
                return pos
        return None

    def _close_position(self, symbol: str, price: float) -> None:
        """Mark the latest open position for *symbol* as closed."""
        pos = self._get_open_position(symbol)
        if pos is None:
            return
        pos["status"] = "closed"
        pos["close_time"] = datetime.utcnow().isoformat()
        pos["close_price"] = price
        logger.info("%s closed at %.2f (trailing stop)", symbol, price)
        # compute PnL and update risk manager
        entry = float(pos.get("price", 0))
        amount = float(pos.get("amount", 0))
        side = pos.get("side", "long")
        pnl = (price - entry) * amount if side == "long" else (entry - price) * amount
        pos["pnl"] = pnl
        self.risk_manager.update_on_close(pnl)
        # remove lock once position is closed
        self.instrument_lock.pop(symbol, None)

    def _load_positions(self) -> List[Dict[str, str]]:
        if self.positions_path.exists():
            with open(self.positions_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                for pos in data:
                    pos.setdefault("status", "closed")
                    pos.setdefault("stop_price", None)
                    pos.setdefault("atr_multiplier", None)
                    pos.setdefault("armed", False)
                    pos.setdefault("trail_mode", "atr")
                    pos.setdefault("strategy", None)
                    pos.setdefault("stop_pct", None)
                    pos.setdefault("signal_source", pos.get("strategy"))
                    pos.setdefault("pnl", None)
                return data
        return []

    def _save_positions(self) -> None:
        with open(self.positions_path, "w", encoding="utf-8") as fh:
            json.dump(self.positions, fh, indent=2)

    def _send_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        stop_distance: float | None,
        atr_value: float | None,
        trailing_mode: str = "atr",
        strategy: str | None = None,
    ) -> None:
        """Send a market order to the exchange and persist it.

        Parameters
        ----------
        symbol: str
            Trading pair (e.g. ``"BTC/USDC"``).
        side: str
            Desired position direction from the strategy, ``"long"`` or ``"short"``.
            It is converted to ``"buy"``/``"sell"`` for the exchange API.
        amount: float
            Quantity of the base asset to trade.
        price: float
            Current market price used by some rules.
        """

        # close any existing open position for this symbol
        self._close_position(symbol, price)

        if amount <= 0:
            logger.warning("Skipping order for %s, amount is %s", symbol, amount)
            return

        # CCXT expects 'buy' or 'sell'; map our signal sides accordingly
        order_side = "buy" if side == "long" else "sell"

        if self.paper:
            order = {"side": order_side, "amount": amount, "paper": True}
        else:
            try:
                order = self.exchange.create_order(symbol, "market", order_side, amount)
            except Exception as exc:  # pragma: no cover - network errors
                logger.error("Order failed: %s", exc)
                order = {"error": str(exc)}

        stop_price = None
        atr_mult = None
        if stop_distance is not None and atr_value:
            direction = 1 if side == "long" else -1
            stop_price = price - direction * stop_distance
            if atr_value:
                atr_mult = stop_distance / atr_value
        stop_pct = stop_distance / price * 100 if stop_distance is not None else None
        
        self.positions.append(
            {
                "time": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "order": order,
                "status": "open",
                "stop_price": stop_price,
                "atr_multiplier": atr_mult,
                "armed": False,
                "trail_mode": trailing_mode,
                "strategy": strategy,
                "stop_pct": stop_pct,
                "signal_source": strategy,
            }
        )

    def fetch_ohlcv(self, symbol: str, limit: int = 2000) -> pd.DataFrame:
        logger.info("Fetching OHLCV for %s", symbol)
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=limit)
        df = pd.DataFrame(
            ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"]
        )
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms", utc=True)
        return df.set_index("Timestamp")

    def _update_open_positions(
        self, df: pd.DataFrame, extras: Dict[str, pd.Series]
    ) -> None:
        """Update trailing stops for all open positions and close if hit."""
        if not self.positions:
            return

        last_close = float(df.iloc[-1]["Close"])
        high_prev = float(df.iloc[-2]["High"])
        low_prev = float(df.iloc[-2]["Low"])

        for pos in self.positions:
            if pos.get("status") != "open":
                continue
            stop = pos.get("stop_price")
            atr_mult = pos.get("atr_multiplier")
            trail_mode = pos.get("trail_mode", "atr")
            side = pos["side"]
            entry = float(pos["price"])
            armed = pos.get("armed", False)
            if stop is None or atr_mult is None:
                continue

            if not armed:
                move = abs(last_close - entry) / entry
                if move >= self.delta_be:
                    direction = 1 if side == "long" else -1
                    pos["stop_price"] = entry + direction * entry * self.delta_be
                    pos["armed"] = True
                    logger.info(
                        "%s trailing stop armed at %.2f",
                        pos["symbol"],
                        pos["stop_price"],
                    )
                continue

            atr_key = "ATR_20" if "ATR_20" in extras else "ATR_14"
            atr_series = extras.get(atr_key)
            if atr_series is None:
                continue
            atr_value = float(atr_series.iloc[-2])

            if trail_mode == "kijun":
                kijun_series = extras.get("Kijun")
                if kijun_series is None:
                    continue
                kijun = float(kijun_series.iloc[-2])
                if side == "long":
                    candidate = kijun + 0.5 * atr_value
                    old = pos["stop_price"]
                    pos["stop_price"] = max(old, candidate)
                    if pos["stop_price"] != old:
                        logger.debug(
                            "%s stop moved to %.2f", pos["symbol"], pos["stop_price"]
                        )
                    if last_close <= pos["stop_price"]:
                        self._close_position(pos["symbol"], last_close)
                else:
                    candidate = kijun - 0.5 * atr_value
                    old = pos["stop_price"]
                    pos["stop_price"] = min(old, candidate)
                    if pos["stop_price"] != old:
                        logger.debug(
                            "%s stop moved to %.2f", pos["symbol"], pos["stop_price"]
                        )
                    if last_close >= pos["stop_price"]:
                        self._close_position(pos["symbol"], last_close)
                continue

            if side == "long":
                candidate = high_prev - atr_mult * atr_value
                old = pos["stop_price"]
                pos["stop_price"] = max(old, candidate)
                if pos["stop_price"] != old:
                    logger.debug(
                        "%s stop moved to %.2f", pos["symbol"], pos["stop_price"]
                    )
                if last_close <= pos["stop_price"]:
                    self._close_position(pos["symbol"], last_close)
            else:
                candidate = low_prev + atr_mult * atr_value
                old = pos["stop_price"]
                pos["stop_price"] = min(old, candidate)
                if pos["stop_price"] != old:
                    logger.debug(
                        "%s stop moved to %.2f", pos["symbol"], pos["stop_price"]
                    )
                if last_close >= pos["stop_price"]:
                    self._close_position(pos["symbol"], last_close)

    def run_once(self, symbol: str, df: Optional[pd.DataFrame] = None) -> None:
        if df is None:
            df = self.fetch_ohlcv(symbol)
        self.risk_manager.record_heartbeat()

        # compute shared indicators
        extras = {}
        # Example: compute ATR 20 for all strategies needing it
        from .utils import compute_atr, compute_ichimoku

        extras["ATR_20"] = compute_atr(df, 20)
        extras["ATR_14"] = compute_atr(df, 14)
        ich = compute_ichimoku(df)
        extras["Kijun"] = ich["kijun"]

        last_candle = df.iloc[-1]
        price = float(last_candle["Close"])
        time = last_candle.name.tz_convert(timezone.utc)

        # update existing position stops first
        self._update_open_positions(df, extras)
        self._save_positions()

        if self._get_open_position(symbol) is not None:
            return

        # gather signals from all strategies
        signals = {}
        for strat_cls in self.strategies:
            signal = strat_cls.generate_signal(df, extras)
            if signal.action != "flat":
                signals[strat_cls.name] = signal

        long_names = [n for n, s in signals.items() if s.action == "long"]
        short_names = [n for n, s in signals.items() if s.action == "short"]
        top_names = {"EMA20_100", "Donchian20", "BollingerSqueeze"}

        def has_top(name_list: list[str]) -> bool:
            return any(n in top_names for n in name_list)

        chosen = None
        if len(long_names) >= 3 and has_top(long_names):
            # Pick strategy with widest stop distance for determinism
            pick = max(
                long_names,
                key=lambda n: (
                    signals[n].stop_distance or 0,
                    n,
                ),
            )
            chosen_sig = signals[pick]
            chosen = ("long", pick, chosen_sig)
        elif len(short_names) >= 3 and has_top(short_names):
            pick = max(
                short_names,
                key=lambda n: (
                    signals[n].stop_distance or 0,
                    n,
                ),
            )
            chosen_sig = signals[pick]
            chosen = ("short", pick, chosen_sig)

        if chosen:
            side, strat_name, ref_signal = chosen
            logger.info("%s %s consensus %s", time, symbol, side.upper())
            atr_value = None
            if ref_signal.stop_distance is not None:
                if "ATR_20" in extras:
                    atr_value = float(extras["ATR_20"].iloc[-1])
                elif "ATR_14" in extras:
                    atr_value = float(extras["ATR_14"].iloc[-1])
            # risk manager check
            open_value = sum(
                p.get("amount", 0) * float(p.get("price", price))
                for p in self.positions
                if p.get("status") == "open"
            )
            ticker = self.exchange.fetch_ticker(symbol)
            volume_24h = float(ticker.get("quoteVolume", 0))
            allowed, amount = self.risk_manager.allows_new_position(
                symbol,
                price,
                ref_signal.stop_distance or 0,
                open_value,
                strat_name,
                atr_value or 0,
                volume_24h,
            )
            if allowed:
                self._send_order(
                    symbol,
                    side,
                    amount,
                    price,
                    ref_signal.stop_distance,
                    atr_value,
                    ref_signal.trailing_mode,
                    strat_name,
                )
            self._save_positions()

    def export_csv(self, path: Path = Path("trades.csv")) -> Dict[str, float]:
        """Export closed positions to CSV and return KPIs (CAGR, MDD)."""
        if not self.positions:
            return {"CAGR": 0.0, "MDD": 0.0}
        df = pd.DataFrame(self.positions)
        if df.empty:
            return {"CAGR": 0.0, "MDD": 0.0}
        df_closed = df[df["status"] == "closed"].copy()
        if df_closed.empty:
            return {"CAGR": 0.0, "MDD": 0.0}
        df_closed["time"] = pd.to_datetime(df_closed["time"])
        df_closed["close_time"] = pd.to_datetime(df_closed["close_time"])
        if "pnl" not in df_closed:
            df_closed["pnl"] = (
                df_closed["close_price"] - df_closed["price"]
            ) * df_closed["amount"]
        df_closed.to_csv(path, index=False)

        start_equity = float(self.risk_manager.config.get("starting_equity", 0))
        equity_curve = start_equity + df_closed["pnl"].cumsum()
        years = (
            (df_closed["close_time"].iloc[-1] - df_closed["time"].iloc[0]).days
            / 365.0
        ) or 1.0
        final = equity_curve.iloc[-1]
        cagr = (final / start_equity) ** (1 / years) - 1 if start_equity else 0.0
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        mdd = float(drawdown.min()) if not drawdown.empty else 0.0
        return {"CAGR": float(cagr), "MDD": mdd}



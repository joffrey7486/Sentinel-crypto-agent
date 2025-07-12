from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


class RiskManager:
    """Simple risk management engine implementing multiple rules.

    The manager keeps track of equity and daily P&L to enforce risk limits such
    as maximum exposure, daily loss limits and overall drawdown. Position sizing
    is based on the distance to the stop using ATR.
    """

    def __init__(self, config_path: Path = Path("risk.yml")) -> None:
        self.config = self._load_config(config_path)
        self.equity = float(self.config.get("starting_equity", 0))
        self.equity_high = self.equity
        self.daily_start_equity = self.equity
        self.daily_pnl = 0.0
        self.loss_streak = 0
        self.pause_until: datetime | None = None
        self.mdd_triggered = False
        self.drawdown_recovery: float | None = None
        self.last_heartbeat = datetime.now(timezone.utc)
        self.last_day = self.last_heartbeat.date()
        self.log_path = Path("risk_events.log")

    @staticmethod
    def _load_config(path: Path) -> Dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        return {}

    def log_event(self, msg: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{timestamp} {msg}\n")
        logger.info(msg)

    # --- Equity tracking -------------------------------------------------
    def new_day(self) -> None:
        self.daily_start_equity = self.equity
        self.daily_pnl = 0.0

    def update_on_close(self, pnl: float) -> None:
        self.equity += pnl
        self.daily_pnl += pnl
        if pnl < 0:
            self.loss_streak += 1
        elif pnl > 0:
            self.loss_streak = 0
        self.equity_high = max(self.equity_high, self.equity)

    def record_heartbeat(self) -> None:
        now = datetime.now(timezone.utc)
        self.last_heartbeat = now
        if now.date() != self.last_day:
            self.new_day()
            self.last_day = now.date()

    # --- Rules -----------------------------------------------------------
    def risk_per_trade(self, stop_distance: float) -> float:
        """Return trade size based on ATR stop distance and risk settings."""

        pct = float(
            self.config.get("risk_per_trade", self.config.get("risk_per_trade_pct", 0.01))
        )
        if self.loss_streak >= int(self.config.get("loss_streak_limit", 4)):
            pct *= 0.5
        capital = self.equity
        if capital <= 0 or stop_distance <= 0:
            return 0.0
        # size = equity * risk_per_trade / ATR stop distance
        return (capital * pct) / stop_distance

    def exposure_ok(self, open_value: float, new_value: float) -> bool:
        max_pct = float(self.config.get("max_exposure_pct", 0.3))
        tot = open_value + new_value
        if self.equity <= 0:
            return False
        return tot / self.equity <= max_pct

    def daily_loss_ok(self) -> bool:
        if self.pause_until and datetime.now(timezone.utc) < self.pause_until:
            return False
        limit_pct = float(self.config.get("daily_loss_limit", self.config.get("daily_loss_limit_pct", 0.02)))
        if self.daily_pnl <= -self.daily_start_equity * limit_pct:
            self.pause_until = datetime.now(timezone.utc) + timedelta(hours=24)
            return False
        return True

    def drawdown_ok(self) -> bool:
        limit_pct = float(self.config.get("max_drawdown", self.config.get("max_drawdown_pct", 0.1)))
        if self.equity_high == 0:
            return True
        drop = (self.equity_high - self.equity) / self.equity_high
        if drop >= limit_pct:
            self.mdd_triggered = True
            self.drawdown_recovery = self.equity_high * (1 - limit_pct / 2)
        if self.mdd_triggered:
            if self.equity >= (self.drawdown_recovery or 0):
                self.mdd_triggered = False
                return True
            return False
        return True

    def volatility_ok(self, atr: float, close: float, strategy: str) -> bool:
        threshold = float(self.config.get("volatility_threshold", 0.007))
        blocked = {"Donchian20", "BollingerSqueeze", "SARFlip"}
        if strategy in blocked and close > 0 and atr / close < threshold:
            return False
        return True

    def liquidity_ok(self, amount: float, volume_24h: float) -> bool:
        max_pct = float(self.config.get("liquidity_pct", 0.0004))
        if volume_24h <= 0:
            return False
        return (amount / volume_24h) <= max_pct

    def time_ok(self) -> bool:
        hours = self.config.get("block_hours", [])
        now = datetime.now(timezone.utc).hour
        return now not in hours

    def heartbeat_ok(self) -> bool:
        timeout = int(self.config.get("heartbeat_timeout", 5))
        delta = datetime.now(timezone.utc) - self.last_heartbeat
        return delta.total_seconds() <= timeout

    def allows_new_position(
        self,
        symbol: str,
        price: float,
        stop_distance: float,
        open_value: float,
        strategy: str,
        atr: float,
        volume_24h: float,
    ) -> Tuple[bool, float]:
        """Return (allowed, size) for a new position."""
        amount = self.risk_per_trade(stop_distance)
        new_value = amount * stop_distance
        if not self.exposure_ok(open_value, price * amount):
            self.log_event(f"Exposure cap block on {symbol}")
            return False, 0.0
        if not self.daily_loss_ok():
            self.log_event("Daily loss limit reached")
            return False, 0.0
        if not self.drawdown_ok():
            self.log_event("Max drawdown breached")
            return False, 0.0
        if not self.volatility_ok(atr, price, strategy):
            self.log_event(f"Volatility filter block on {symbol}")
            return False, 0.0
        if not self.liquidity_ok(amount * price, volume_24h):
            self.log_event(f"Liquidity guard block on {symbol}")
            return False, 0.0
        if not self.time_ok():
            self.log_event("Time-of-day block")
            return False, 0.0
        if not self.heartbeat_ok():
            self.log_event("Heartbeat stale; trading paused")
            return False, 0.0
        # correlation & tech risk rules simplified as pair uniqueness
        return True, amount


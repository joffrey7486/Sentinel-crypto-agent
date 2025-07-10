"""CLI entry point for Sentinel Crypto Agent."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import time as time_mod

from core.engine import Engine
from strategies import (
    EMA20_100,
    Donchian20,
    BollingerSqueeze,
    IchimokuKumo,
    MACDZeroCross,
    VWAPPullback,
    KeltnerUpperRide,
    SMA50Pullback,
    SARFlip,
    RSIDivergence,
)


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Sentinel Crypto Agent CLI")
    parser.add_argument("--pair", default="BTC/USDC", help="Trading pair, e.g., BTC/USDC")
    parser.add_argument("--once", action="store_true", help="Run a single 4h candle evaluation")
    args = parser.parse_args()

    eng = Engine()
    # register strategies
    eng.register_strategy(EMA20_100)
    eng.register_strategy(Donchian20)
    eng.register_strategy(BollingerSqueeze)
    eng.register_strategy(IchimokuKumo)
    eng.register_strategy(MACDZeroCross)
    eng.register_strategy(VWAPPullback)
    eng.register_strategy(KeltnerUpperRide)
    eng.register_strategy(SMA50Pullback)
    eng.register_strategy(SARFlip)
    eng.register_strategy(RSIDivergence)

    if args.once:
        eng.run_once(args.pair)
        return

    print("[Sentinel] Running live mode. Evaluating every 4H close UTC…")
    while True:
        now = datetime.now(timezone.utc)
        if now.hour % 4 == 0 and now.minute < 3:
            eng.run_once(args.pair)
            time_mod.sleep(60 * 180)  # wait 3h to avoid duplicate run
        else:
            time_mod.sleep(60)


if __name__ == "__main__":
    main()

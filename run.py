"""CLI entry point for Sentinel Crypto Agent."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import time as time_mod

from core.engine import Engine
from core.api import init_api
import threading
import uvicorn
import webview
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

    app = init_api(eng)

    def api_runner():  # pragma: no cover - server loop
        uvicorn.run(app, port=8080, log_level="warning")

    threading.Thread(target=api_runner, daemon=True).start()

    def engine_loop():
        while eng.running:
            now = datetime.now(timezone.utc)
            if now.hour % 4 == 0 and now.minute < 3:
                eng.run_once(args.pair)
                for _ in range(180):
                    if not eng.running:
                        return
                    time_mod.sleep(60)
            else:
                time_mod.sleep(60)

    threading.Thread(target=engine_loop, daemon=True).start()

    window = webview.create_window(
        "Sentinel Dashboard",
        "http://127.0.0.1:8080/dashboard.html",
        width=900,
        height=700,
    )
    window.events.closed += lambda *a: eng.stop()
    webview.start()


if __name__ == "__main__":
    main()

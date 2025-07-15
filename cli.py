"""Command line interface for Sentinel Crypto Agent."""
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime, timezone
import time
import pandas as pd

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


def _register_all(eng: Engine) -> Engine:
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
    return eng


def cmd_backtest(args: argparse.Namespace) -> None:
    eng = _register_all(Engine(paper=True))
    df = eng.fetch_ohlcv(args.pair, limit=2000)
    df = df[df.index >= pd.Timestamp("2020-01-01", tz="UTC")]
    for i in range(len(df)):
        eng.run_once(args.pair, df=df.iloc[: i + 1])
    kpi = eng.export_csv(Path("trades.csv"))
    print(f"CAGR: {kpi['CAGR']:.2%}  MDD: {kpi['MDD']:.2%}")


def cmd_live(args: argparse.Namespace) -> None:
    eng = _register_all(Engine(paper=args.paper))
    print("[Sentinel] Running live mode. Evaluating every 4H close UTC…")
    while True:
        now = datetime.now(timezone.utc)
        if now.hour % 4 == 0 and now.minute < 3:
            eng.run_once(args.pair)
            time.sleep(60 * 180)
        else:
            time.sleep(60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_back = sub.add_parser("backtest", help="Run backtest from 2020")
    p_back.add_argument("--pair", default="BTC/USDC")

    p_live = sub.add_parser("live", help="Run live mode")
    p_live.add_argument("--pair", default="BTC/USDC")
    p_live.add_argument("--paper", action="store_true", help="Simulated orders")

    args = parser.parse_args()
    if args.cmd == "backtest":
        cmd_backtest(args)
    elif args.cmd == "live":
        cmd_live(args)


if __name__ == "__main__":
    main()

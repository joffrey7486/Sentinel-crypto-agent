from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .engine import Engine

app = FastAPI()
engine: Engine | None = None

STATIC_DIR = Path(__file__).resolve().parent.parent / "services" / "static"
LOG_PATH = Path("risk_events.log")


def init_api(eng: Engine) -> FastAPI:
    """Bind an :class:`Engine` instance to the API and return the app."""
    global engine
    engine = eng
    return app


@app.get("/status")
def get_status():
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    now = datetime.now(timezone.utc)
    next_hour = (now.hour // 4 + 1) * 4
    day = now
    if next_hour >= 24:
        next_hour -= 24
        day = now + timedelta(days=1)
    next_cycle = day.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    risk = engine.risk_manager
    if risk.equity_high:
        drawdown = (risk.equity - risk.equity_high) / risk.equity_high * 100
    else:
        drawdown = 0.0
    return {
        "alive": True,
        "version": "0.1.0",
        "next_cycle": next_cycle.strftime("%Y-%m-%dT%H:%MZ"),
        "metrics": {
            "daily_pnl": risk.daily_pnl,
            "drawdown": drawdown,
        },
    }


@app.get("/positions")
def get_positions():
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    return [p for p in engine.positions if p.get("status") == "open"]


@app.get("/logs/tail")
def tail_logs(n: int = 50):
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-n:]
    else:
        lines = []
    return {"lines": [line.rstrip() for line in lines]}


@app.get("/dashboard.html")
def dashboard():
    file_path = STATIC_DIR / "dashboard.html"
    return FileResponse(file_path)

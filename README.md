# Sentinel Crypto Agent

A lightweight **crypto-trading signal engine** written in Python.  
Sentinel fetches 4-hour OHLCV data from a CCXT-compatible exchange (Binance by default),
computes technical indicators once per candle close and lets a collection of **pluggable trading strategies**
decide whether to open a *long* or *short* position.

* 🛠 Easy to extend – drop a new strategy file in `strategies/` and register the class.
* 🧮 Indicator helpers – ATR, EMA, RSI, VWAP, Bollinger, Keltner, Ichimoku, MACD, PSAR…
* 💾 Positions persisted to `positions.json` for audit & back-testing.
* 🔔 Instrument lock to avoid multiple strategies fighting over the same symbol.
* ⏱ Runs live every 4 h or **once-off** for back-testing.

---

## 1. Quick start

```bash
# 1. Clone & enter the repo
$ git clone https://github.com/joffrey7486/Sentinel-crypto-agent.git
$ cd Sentinel-crypto-agent

# 2. Create a virtual environment (optional but recommended)
$ python -m venv .venv
$ source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
$ pip install -r requirements.txt  # ← create if you don’t have one – see below

# 4. Add your exchange API keys (env variables)
$ set API_KEY=xxxxxxxxxxxxxxxxxxx         # Windows PowerShell
$ set API_SECRET=yyyyyyyyyyyyyyyyyyyyyyy

# 5. (Optional) tweak `config.yaml`
# position_size_pct: 0.02  # risk 2 % of capital per trade

# 6. Run once on the latest closed 4 h candle
$ python run.py --pair BTC/USDC --once

# 7. Run in live-mode (evaluates every 4 h)
$ python run.py --pair BTC/USDC
```

> **Note** – Binance is the default exchange.  Any CCXT-supported exchange can be used by
> passing the `exchange_id` parameter when instantiating `Engine`.

---

## 2. Project layout

```
.
├── core/                # Engine & shared utilities
│   ├── engine.py        # Main orchestration logic
│   └── utils.py         # Indicators + Signal object
├── strategies/          # Plug-and-play strategy classes
│   ├── base.py          # Helper parent class
│   └── …                # EMA20_100, MACDZeroCross, VWAPPullback, …
├── positions.json       # Trade log (auto-created)
├── config.yaml          # Simple runtime settings (risk % etc.)
├── run.py               # CLI entry-point – registers strategies & starts the loop
└── README.md            # You are here 🖖
```

### Engine workflow

1. Load `config.yaml` and exchange credentials (from env vars).
2. Fetch latest **4 h** OHLCV candles via CCXT.
3. Compute common indicators (ATR, etc.) once for all strategies.
4. Iterate over registered strategy classes until one returns a non-`flat` signal.
5. Send a **market order** sized by `position_size_pct`.
6. Persist the trade to `positions.json` and lock the symbol for that strategy until flat.

---

## 3. Configuration

`config.yaml` (auto-created on first run if missing):

```yaml
# Risk management
position_size_pct: 0.01   # 1 % of available quote asset per trade
```

Environment variables required:

* `API_KEY` – exchange public key
* `API_SECRET` – exchange secret key

---

## 4. Extending – write your own strategy ⚡

1. Create a new file in `strategies/` (e.g. `myawesomestrat.py`).
2. Sub-class `strategies.base.BaseStrategy` **or** implement the same interface:

```python
from __future__ import annotations
import pandas as pd
from core.utils import Signal
from strategies.base import BaseStrategy

class MyAwesomeStrat(BaseStrategy):
    name = "MyAwesomeStrat"

    @classmethod
    def generate_signal(cls, df: pd.DataFrame, extras: dict[str, pd.Series]):
        # Implement your logic – return Signal("long"|"short"|"flat")
        return Signal("flat")
```

3. Register the class in `run.py` right after the other imports:

```python
from strategies.myawesomestrat import MyAwesomeStrat
eng.register_strategy(MyAwesomeStrat)
```

That’s it – the engine will now call your strategy on each cycle.

---

## 5. Back-testing with historical data 🕰️

`Engine.run_once()` accepts a pre-loaded DataFrame, so you can easily
loop over CSV files or fetched data to measure performance off-line:

```python
import pandas as pd
from core.engine import Engine

df = pd.read_csv("BTCUSDC-4h.csv", parse_dates=["Timestamp"], index_col="Timestamp")
eng = Engine()
eng.register_strategy(MACDZeroCross)
eng.run_once("BTC/USDC", df=df)
```

---

## 6. Requirements

```
python >= 3.11
ccxt >= 4.0.0
pandas >= 2.0
numpy >= 1.25
yaml (PyYAML)
```

Create `requirements.txt` if you need one:

```
ccxt>=4.0
pandas>=2.0
numpy>=1.25
PyYAML>=6.0
```

---

## 7. Disclaimer

This project is **experimental** and provided **for educational purposes only**.  
Trading cryptocurrencies involves significant risk. Use at your own discretion; the
authors accept no liability for financial losses.

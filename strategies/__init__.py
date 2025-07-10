"""Strategy package: expose all strategy classes."""
from importlib import import_module
from types import ModuleType
from typing import Dict, Type

from core.engine import StrategyBase

__all__ = [
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
]

_strategy_modules: Dict[str, ModuleType] = {}

# Dynamically import strategy modules to avoid circular import issues
for _name in __all__:
    _module = import_module(f"strategies.{_name.lower()}")
    _strategy_modules[_name] = _module
    globals()[_name] = getattr(_module, _name)  # type: ignore

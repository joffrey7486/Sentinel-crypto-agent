from pathlib import Path
from core.risk_manager import RiskManager


def test_risk_per_trade_sizing():
    rm = RiskManager(Path("risk.yml"))
    rm.equity = 10000
    size = rm.risk_per_trade(100)
    assert round(size, 2) == 1.0


def test_daily_loss_limit():
    rm = RiskManager(Path("risk.yml"))
    rm.equity = 10000
    rm.daily_start_equity = 10000
    rm.update_on_close(-300)  # 3% loss
    assert not rm.daily_loss_ok()


def test_exposure_cap():
    rm = RiskManager(Path("risk.yml"))
    rm.equity = 10000
    assert rm.exposure_ok(1000, 1500)
    assert not rm.exposure_ok(2500, 1000)

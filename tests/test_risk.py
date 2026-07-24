import pytest

from fx_bot.instruments import pip_size, pips_to_price, price_to_pips
from fx_bot.risk import RiskManager


def test_pip_size():
    assert pip_size("USD_JPY") == 0.01
    assert pip_size("EUR_USD") == 0.0001


def test_pip_conversion_roundtrip():
    assert price_to_pips(pips_to_price(20, "USD_JPY"), "USD_JPY") == pytest.approx(20)


def test_position_size_scales_with_risk():
    # 資金100万, リスク1% = 1万円をリスク。SL 20pips(=0.20円/unit) → 5万ユニット
    rm = RiskManager(risk_per_trade_pct=1.0, stop_loss_pips=20)
    plan = rm.plan_entry("USD_JPY", direction=1, balance=1_000_000, entry_price=150.0)
    assert plan.units == pytest.approx(50_000, rel=1e-3)
    assert plan.risk_amount == pytest.approx(10_000)


def test_stop_and_take_profit_placement():
    rm = RiskManager(stop_loss_pips=20, take_profit_pips=40)
    long_plan = rm.plan_entry("USD_JPY", 1, 1_000_000, 150.0)
    assert long_plan.stop_loss < 150.0 < long_plan.take_profit
    short_plan = rm.plan_entry("USD_JPY", -1, 1_000_000, 150.0)
    assert short_plan.take_profit < 150.0 < short_plan.stop_loss
    assert short_plan.units < 0


def test_daily_loss_halt():
    rm = RiskManager(max_daily_loss_pct=5.0)
    rm.start_day(balance=1_000_000)
    assert not rm.trading_halted(current_balance=970_000)   # -3%: 継続
    assert rm.trading_halted(current_balance=940_000)       # -6%: 停止

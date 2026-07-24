import pytest

from fx_bot.backtest import BacktestEngine
from fx_bot.data import generate_synthetic_candles
from fx_bot.risk import RiskManager
from fx_bot.strategies import MACrossStrategy


def test_backtest_runs_end_to_end():
    df = generate_synthetic_candles("USD_JPY", "H1", count=1000)
    engine = BacktestEngine("USD_JPY", RiskManager(), initial_balance=1_000_000)
    result = engine.run(df, MACrossStrategy(fast=10, slow=30))

    # パイプラインが最後まで回り、結果が整合していること
    assert result.equity_curve is not None
    assert len(result.equity_curve) == len(df)
    assert result.num_trades >= 0
    assert 0 <= result.win_rate <= 100
    # 最終資金 ≈ 初期資金 + 全トレードのPnL合計
    total_pnl = sum(t.pnl for t in result.trades)
    assert result.final_balance == pytest.approx(result.initial_balance + total_pnl)


def test_flat_data_no_trades():
    # 完全フラットな価格ではクロスが起きず、ロングのみ設定ならトレードは発生しない
    df = generate_synthetic_candles("USD_JPY", "H1", count=200)
    df[["open", "high", "low", "close"]] = 150.0
    engine = BacktestEngine("USD_JPY", RiskManager())
    result = engine.run(df, MACrossStrategy(fast=5, slow=20, allow_short=False))
    assert result.num_trades == 0
    assert result.final_balance == result.initial_balance

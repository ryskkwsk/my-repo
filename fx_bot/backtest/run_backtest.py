"""バックテスト実行の CLI エントリ。

例:
    python -m fx_bot.backtest.run_backtest
    python -m fx_bot.backtest.run_backtest --instrument USD_JPY --fast 20 --slow 50
"""
from __future__ import annotations

import argparse

from fx_bot.backtest.engine import BacktestEngine
from fx_bot.config import load_settings
from fx_bot.data import get_candles
from fx_bot.risk import RiskManager
from fx_bot.strategies import MACrossStrategy


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="移動平均クロスのバックテスト")
    parser.add_argument("--instrument", default=settings.instrument)
    parser.add_argument("--granularity", default=settings.granularity)
    parser.add_argument("--count", type=int, default=2000, help="ローソク足の本数")
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--balance", type=float, default=1_000_000)
    parser.add_argument("--spread-pips", type=float, default=0.8)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    df = get_candles(
        instrument=args.instrument,
        granularity=args.granularity,
        count=args.count,
        use_cache=not args.no_cache,
    )
    print(f"[data] {len(df)} 本のローソク足 "
          f"({df.index[0]} 〜 {df.index[-1]})")

    strategy = MACrossStrategy(fast=args.fast, slow=args.slow)
    risk = RiskManager(
        risk_per_trade_pct=settings.risk_per_trade_pct,
        stop_loss_pips=settings.stop_loss_pips,
        take_profit_pips=settings.take_profit_pips,
        max_daily_loss_pct=settings.max_daily_loss_pct,
    )
    engine = BacktestEngine(
        instrument=args.instrument,
        risk_manager=risk,
        initial_balance=args.balance,
        spread_pips=args.spread_pips,
    )

    result = engine.run(df, strategy)
    print()
    print(f"戦略: {strategy.name}(fast={args.fast}, slow={args.slow})  "
          f"通貨ペア: {args.instrument}  粒度: {args.granularity}")
    print(result.summary())


if __name__ == "__main__":
    main()

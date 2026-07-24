"""FX 向けの軽量バックテストエンジン。

設計方針:
- 未来を見ない: バー i のデータで判断し、執行は「次のバーの始値」で行う。
- 現実的なコスト: エントリーごとにスプレッド（pips）を差し引く。
- SL/TP を各バーの高値/安値でチェックして決済する。
- ポジションサイズはリスク管理層と同じ「資金 × リスク% ÷ 損切り幅」で決める。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fx_bot.instruments import pips_to_price, price_to_pips
from fx_bot.risk import RiskManager
from fx_bot.strategies.base import Strategy


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int          # +1 long / -1 short
    entry_price: float
    exit_price: float
    units: int
    pnl: float              # 口座通貨建て損益
    reason: str             # "signal" / "stop_loss" / "take_profit" / "end"


@dataclass
class BacktestResult:
    initial_balance: float
    final_balance: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series | None = None

    @property
    def total_return_pct(self) -> float:
        return (self.final_balance / self.initial_balance - 1) * 100

    @property
    def num_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades) * 100

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = -sum(t.pnl for t in self.trades if t.pnl < 0)
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @property
    def max_drawdown_pct(self) -> float:
        if self.equity_curve is None or self.equity_curve.empty:
            return 0.0
        running_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - running_max) / running_max
        return abs(drawdown.min()) * 100

    def summary(self) -> str:
        lines = [
            "===== バックテスト結果 =====",
            f"初期資金        : {self.initial_balance:,.0f}",
            f"最終資金        : {self.final_balance:,.0f}",
            f"総リターン      : {self.total_return_pct:+.2f}%",
            f"トレード数      : {self.num_trades}",
            f"勝率            : {self.win_rate:.1f}%",
            f"プロフィットファクター: {self.profit_factor:.2f}",
            f"最大ドローダウン: {self.max_drawdown_pct:.2f}%",
        ]
        return "\n".join(lines)


class BacktestEngine:
    def __init__(
        self,
        instrument: str,
        risk_manager: RiskManager,
        initial_balance: float = 1_000_000,
        spread_pips: float = 0.8,
    ):
        self.instrument = instrument
        self.risk = risk_manager
        self.initial_balance = initial_balance
        self.spread_pips = spread_pips

    def run(self, df: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        signals = strategy.generate_signals(df)
        # 執行は次バー始値。判断はバー i、執行は i+1 なので target を1つずらす。
        target = signals.shift(1).fillna(0).astype(int)

        balance = self.initial_balance
        spread_cost_price = pips_to_price(self.spread_pips, self.instrument)

        position = 0        # +1 / 0 / -1
        entry_price = 0.0
        units = 0
        sl = tp = 0.0
        entry_time = None

        trades: list[Trade] = []
        equity = []
        opens = df["open"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        times = df.index

        def close_position(exit_price: float, exit_time, reason: str):
            nonlocal balance, position, units, entry_price, entry_time
            pnl = (exit_price - entry_price) * units  # units は符号付き
            balance += pnl
            trades.append(
                Trade(
                    entry_time=entry_time, exit_time=exit_time,
                    direction=position, entry_price=entry_price,
                    exit_price=exit_price, units=units, pnl=pnl, reason=reason,
                )
            )
            position, units, entry_price, entry_time = 0, 0, 0.0, None

        for i in range(len(df)):
            price_open = opens[i]

            # 1) 保有中なら SL/TP を高値・安値で判定（同バー内で先に処理）
            if position != 0:
                if position == 1:
                    if lows[i] <= sl:
                        close_position(sl, times[i], "stop_loss")
                    elif highs[i] >= tp:
                        close_position(tp, times[i], "take_profit")
                else:  # short
                    if highs[i] >= sl:
                        close_position(sl, times[i], "stop_loss")
                    elif lows[i] <= tp:
                        close_position(tp, times[i], "take_profit")

            # 2) シグナルに応じてポジション調整（次バー始値で執行済みの target を使用）
            desired = target.iloc[i]
            if position != 0 and desired != position:
                close_position(price_open, times[i], "signal")

            if position == 0 and desired != 0:
                plan = self.risk.plan_entry(
                    self.instrument, desired, balance, price_open
                )
                if plan.units != 0:
                    position = desired
                    units = plan.units
                    # スプレッド分だけ不利な価格で約定したものとして反映
                    entry_price = price_open + desired * spread_cost_price
                    sl, tp = plan.stop_loss, plan.take_profit
                    entry_time = times[i]

            # 3) 含み損益込みのエクイティを記録
            mark = opens[i]
            unrealized = (mark - entry_price) * units if position != 0 else 0.0
            equity.append(balance + unrealized)

        # 最終バーで持ち越しがあれば手仕舞い
        if position != 0:
            close_position(opens[-1], times[-1], "end")

        return BacktestResult(
            initial_balance=self.initial_balance,
            final_balance=balance,
            trades=trades,
            equity_curve=pd.Series(equity, index=df.index),
        )

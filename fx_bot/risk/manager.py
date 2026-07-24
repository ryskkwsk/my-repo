"""リスク管理層。

自動売買で資金を守る要。ここが戦略より重要。
- ポジションサイズは「1トレードで失ってよい金額 ÷ 損切り幅」で決める
- 損切り(SL)・利確(TP)価格を計算する
- 1日の最大損失を超えたら発注を止める（自動停止）
"""
from __future__ import annotations

from dataclasses import dataclass

from fx_bot.instruments import pip_size, pips_to_price


@dataclass
class PositionPlan:
    """1回のエントリー計画。"""
    units: int          # 発注ユニット数（+ロング / -ショート）。OANDAは通貨単位
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float  # このトレードで許容した損失額（口座通貨）


class RiskManager:
    def __init__(
        self,
        risk_per_trade_pct: float = 1.0,
        stop_loss_pips: float = 20.0,
        take_profit_pips: float = 40.0,
        max_daily_loss_pct: float = 5.0,
    ):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips
        self.max_daily_loss_pct = max_daily_loss_pct
        self._daily_start_balance: float | None = None
        self._daily_pnl: float = 0.0

    def plan_entry(
        self,
        instrument: str,
        direction: int,      # +1=ロング, -1=ショート
        balance: float,
        entry_price: float,
    ) -> PositionPlan:
        """資金と損切り幅からポジションサイズと SL/TP を計算する。"""
        if direction not in (1, -1):
            raise ValueError("direction は +1 か -1")

        risk_amount = balance * (self.risk_per_trade_pct / 100.0)
        sl_price_dist = pips_to_price(self.stop_loss_pips, instrument)
        tp_price_dist = pips_to_price(self.take_profit_pips, instrument)

        # 損切りまでの1ユニットあたり損失 ≈ 損切り価格幅（決済通貨建て）。
        # JPY建て口座 & 対円ペアを主対象とした簡易計算。厳密な換算は
        # ライブ運用で口座通貨レートを掛けて補正する（TODO）。
        per_unit_loss = sl_price_dist
        units = int(risk_amount / per_unit_loss) if per_unit_loss > 0 else 0
        units *= direction

        stop_loss = entry_price - direction * sl_price_dist
        take_profit = entry_price + direction * tp_price_dist

        return PositionPlan(
            units=units,
            entry_price=entry_price,
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            risk_amount=risk_amount,
        )

    # --- 1日の損失上限による自動停止 ---
    def start_day(self, balance: float) -> None:
        self._daily_start_balance = balance
        self._daily_pnl = 0.0

    def record_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl

    def trading_halted(self, current_balance: float | None = None) -> bool:
        """1日の損失が上限を超えていたら True（発注停止すべき）。"""
        if self._daily_start_balance is None:
            return False
        loss = -self._daily_pnl
        if current_balance is not None:
            loss = self._daily_start_balance - current_balance
        limit = self._daily_start_balance * (self.max_daily_loss_pct / 100.0)
        return loss >= limit

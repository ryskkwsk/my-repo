"""デモ口座でのライブ運用ループ（Step 5）。

⚠ 実際に発注するコードなので、必ず practice(デモ) 環境で使うこと。
1バーごとに:
  1. 最新ローソク足を取得
  2. 戦略でシグナル算出
  3. 現在の建玉と比較し、必要ならリスク管理層のサイズで発注/決済
  4. 1日の損失上限を超えたら停止

まずは --dry-run（発注せずログのみ）で挙動を確認してから実弾に進むこと。
"""
from __future__ import annotations

import time

from fx_bot.broker import OandaClient
from fx_bot.config import load_settings
from fx_bot.data import get_candles
from fx_bot.risk import RiskManager
from fx_bot.strategies import MACrossStrategy
from fx_bot.strategies.base import Signal


class LiveRunner:
    def __init__(self, dry_run: bool = True, poll_seconds: int = 60):
        self.settings = load_settings()
        self.settings.require_credentials()
        if self.settings.is_live:
            raise RuntimeError(
                "現在 OANDA_ENV=live です。まずは practice(デモ) で運用してください。"
            )
        self.dry_run = dry_run
        self.poll_seconds = poll_seconds

        self.client = OandaClient(self.settings)
        self.strategy = MACrossStrategy()
        self.risk = RiskManager(
            risk_per_trade_pct=self.settings.risk_per_trade_pct,
            stop_loss_pips=self.settings.stop_loss_pips,
            take_profit_pips=self.settings.take_profit_pips,
            max_daily_loss_pct=self.settings.max_daily_loss_pct,
        )

    def step(self) -> None:
        """1サイクル分の判断と執行。"""
        inst = self.settings.instrument
        df = get_candles(inst, self.settings.granularity, count=200, use_cache=False)
        signal = self.strategy.latest_signal(df)
        current_units = self.client.open_position_units(inst)
        current_dir = (current_units > 0) - (current_units < 0)  # sign

        balance = self.client.balance()
        if self.risk.trading_halted(current_balance=balance):
            print("[live] 1日の損失上限に到達。発注を停止します。")
            return

        target = int(signal)
        print(f"[live] signal={Signal(signal).name} 建玉={current_units} "
              f"目標={target} 残高={balance:,.0f}")

        if target == current_dir:
            return  # 既に望ましいポジション

        # 望むポジションと違う → 一旦決済してから建て直す
        if current_dir != 0 and not self.dry_run:
            self.client.close_position(inst)

        if target != 0:
            price = self.client.current_price(inst)
            entry = price["ask"] if target > 0 else price["bid"]
            plan = self.risk.plan_entry(inst, target, balance, entry)
            print(f"[live] 発注計画 units={plan.units} "
                  f"SL={plan.stop_loss} TP={plan.take_profit}")
            if not self.dry_run and plan.units != 0:
                self.client.market_order(
                    inst, plan.units, plan.stop_loss, plan.take_profit
                )

    def run(self) -> None:
        mode = "DRY-RUN(発注なし)" if self.dry_run else "LIVE(デモ発注)"
        print(f"[live] 開始 — {mode} / {self.settings.instrument} "
              f"/ {self.settings.granularity} / {self.poll_seconds}s間隔")
        self.risk.start_day(self.client.balance())
        while True:
            try:
                self.step()
            except Exception as exc:  # noqa: BLE001 — 稼働継続のため握りつぶしてログ
                print(f"[live] エラー: {exc}")
            time.sleep(self.poll_seconds)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="デモ口座ライブ運用")
    parser.add_argument("--dry-run", action="store_true",
                        help="発注せずシグナルとログだけ出す")
    parser.add_argument("--poll", type=int, default=60, help="ポーリング秒数")
    args = parser.parse_args()
    LiveRunner(dry_run=args.dry_run, poll_seconds=args.poll).run()

"""OANDA v20 API の薄いラッパー。

デモ(practice)/本番(live) 双方に対応。当面は practice のみで使う。
oandapyV20 は遅延インポートし、バックテストだけ動かす場合に不要な依存を避ける。
"""
from __future__ import annotations

from dataclasses import dataclass

from fx_bot.config import Settings


@dataclass
class AccountSummary:
    account_id: str
    currency: str
    balance: float
    open_position_count: int
    unrealized_pl: float
    margin_available: float


class OandaClient:
    def __init__(self, settings: Settings):
        settings.require_credentials()
        from oandapyV20 import API

        self.settings = settings
        self.api = API(
            access_token=settings.api_token, environment=settings.oanda_env
        )
        self.account_id = settings.account_id

    # --- 口座情報 ---
    def account_summary(self) -> AccountSummary:
        from oandapyV20.endpoints.accounts import AccountSummary as _Summary

        req = _Summary(accountID=self.account_id)
        self.api.request(req)
        acc = req.response["account"]
        return AccountSummary(
            account_id=acc["id"],
            currency=acc["currency"],
            balance=float(acc["balance"]),
            open_position_count=int(acc["openPositionCount"]),
            unrealized_pl=float(acc["unrealizedPL"]),
            margin_available=float(acc["marginAvailable"]),
        )

    def balance(self) -> float:
        return self.account_summary().balance

    # --- 価格 ---
    def current_price(self, instrument: str) -> dict:
        """bid/ask/mid の現在値を返す。"""
        from oandapyV20.endpoints.pricing import PricingInfo

        req = PricingInfo(
            accountID=self.account_id, params={"instruments": instrument}
        )
        self.api.request(req)
        p = req.response["prices"][0]
        bid = float(p["bids"][0]["price"])
        ask = float(p["asks"][0]["price"])
        return {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}

    # --- 発注 ---
    def market_order(
        self,
        instrument: str,
        units: int,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict:
        """成行注文。units は +ロング / -ショート。SL/TP は価格で指定。"""
        from oandapyV20.endpoints.orders import OrderCreate

        order: dict = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }
        if stop_loss is not None:
            order["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
        if take_profit is not None:
            order["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}

        req = OrderCreate(accountID=self.account_id, data=order)
        self.api.request(req)
        return req.response

    def close_position(self, instrument: str) -> dict:
        """指定通貨ペアの建玉を全決済する。"""
        from oandapyV20.endpoints.positions import PositionClose

        data = {"longUnits": "ALL", "shortUnits": "ALL"}
        req = PositionClose(
            accountID=self.account_id, instrument=instrument, data=data
        )
        self.api.request(req)
        return req.response

    def open_position_units(self, instrument: str) -> int:
        """指定通貨ペアの現在の建玉ユニット（+ロング/-ショート/0）を返す。"""
        from oandapyV20.endpoints.positions import OpenPositions

        req = OpenPositions(accountID=self.account_id)
        self.api.request(req)
        for pos in req.response.get("positions", []):
            if pos["instrument"] == instrument:
                return int(pos["long"]["units"]) + int(pos["short"]["units"])
        return 0

"""環境変数（.env）から設定を読み込む。

トークンが無くてもバックテストは動くよう、認証系は「未設定でも例外にしない」
方針にしている。ライブ発注時にだけ require_credentials() で明示的に検証する。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()  # カレントの .env を読み込む（存在しなくても無害）
except ImportError:  # python-dotenv 未インストールでも動作させる
    pass


@dataclass(frozen=True)
class Settings:
    # --- OANDA 認証 ---
    oanda_env: str          # "practice"(デモ) or "live"(本番)
    api_token: str | None
    account_id: str | None

    # --- 取引デフォルト ---
    instrument: str
    granularity: str

    # --- リスク管理 ---
    risk_per_trade_pct: float
    stop_loss_pips: float
    take_profit_pips: float
    max_daily_loss_pct: float

    @property
    def is_live(self) -> bool:
        return self.oanda_env.lower() == "live"

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_token and self.account_id)

    def require_credentials(self) -> None:
        """ライブ/デモ発注前に呼ぶ。未設定なら分かりやすいエラーで止める。"""
        if not self.has_credentials:
            raise RuntimeError(
                "OANDA の認証情報が未設定です。.env に OANDA_API_TOKEN と "
                "OANDA_ACCOUNT_ID を設定してください（.env.example を参照）。"
            )


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def load_settings() -> Settings:
    return Settings(
        oanda_env=os.getenv("OANDA_ENV", "practice"),
        api_token=os.getenv("OANDA_API_TOKEN") or None,
        account_id=os.getenv("OANDA_ACCOUNT_ID") or None,
        instrument=os.getenv("DEFAULT_INSTRUMENT", "USD_JPY"),
        granularity=os.getenv("DEFAULT_GRANULARITY", "H1"),
        risk_per_trade_pct=_get_float("RISK_PER_TRADE_PCT", 1.0),
        stop_loss_pips=_get_float("STOP_LOSS_PIPS", 20.0),
        take_profit_pips=_get_float("TAKE_PROFIT_PIPS", 40.0),
        max_daily_loss_pct=_get_float("MAX_DAILY_LOSS_PCT", 5.0),
    )

"""OANDA 接続確認スクリプト（Step 1）。

.env に認証情報を設定したあと、これを実行して疎通を確認する:
    python scripts/check_connection.py

口座残高と対象通貨ペアの現在値が表示されれば成功。
"""
from __future__ import annotations

import sys
from pathlib import Path

# `pip install -e .` していなくても実行できるようリポジトリ直下を import パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fx_bot.broker import OandaClient
from fx_bot.config import load_settings


def main() -> int:
    settings = load_settings()

    if not settings.has_credentials:
        print("✗ 認証情報が未設定です。")
        print("  .env.example をコピーして .env を作り、OANDA_API_TOKEN と")
        print("  OANDA_ACCOUNT_ID を設定してください。")
        return 1

    print(f"環境: {settings.oanda_env}  通貨ペア: {settings.instrument}")
    try:
        client = OandaClient(settings)
        acc = client.account_summary()
        price = client.current_price(settings.instrument)
    except Exception as exc:  # noqa: BLE001 — 接続確認では原因をそのまま出す
        print(f"✗ 接続失敗: {exc}")
        return 1

    print("✓ 接続成功")
    print(f"  口座ID   : {acc.account_id}")
    print(f"  残高     : {acc.balance:,.2f} {acc.currency}")
    print(f"  建玉数   : {acc.open_position_count}")
    print(f"  余剰証拠金: {acc.margin_available:,.2f} {acc.currency}")
    print(f"  {settings.instrument} 現在値: "
          f"bid={price['bid']} ask={price['ask']} mid={price['mid']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

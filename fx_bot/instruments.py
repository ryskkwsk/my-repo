"""通貨ペアに依存する共通ユーティリティ（pip の定義など）。"""
from __future__ import annotations


def pip_size(instrument: str) -> float:
    """1 pip の価格幅を返す。

    JPY を含むペア（例: USD_JPY）は 0.01、それ以外（例: EUR_USD）は 0.0001。
    """
    return 0.01 if instrument.upper().endswith("JPY") else 0.0001


def price_to_pips(price_diff: float, instrument: str) -> float:
    """価格差を pips に変換する。"""
    return price_diff / pip_size(instrument)


def pips_to_price(pips: float, instrument: str) -> float:
    """pips を価格差に変換する。"""
    return pips * pip_size(instrument)

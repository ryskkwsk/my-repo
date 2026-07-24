"""移動平均クロス戦略。

短期SMA が長期SMA を上抜け → ロング / 下抜け → ショート。
最初の1本として最適: ロジックが単純でバグりにくく、「発注〜決済の一連が
正しく回るか」の検証に集中できる。中身はあとから差し替え可能。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy


class MACrossStrategy(Strategy):
    name = "ma_cross"

    def __init__(self, fast: int = 20, slow: int = 50, allow_short: bool = True):
        if fast >= slow:
            raise ValueError(f"fast({fast}) は slow({slow}) より小さくしてください")
        self.fast = fast
        self.slow = slow
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()

        # 短期が長期より上ならロング志向。allow_short=False なら「上=ロング/下=ノーポジ」
        long_side = np.where(fast_ma > slow_ma, 1, -1 if self.allow_short else 0)
        signal = pd.Series(long_side, index=df.index, dtype="int64")

        # 移動平均が確定していない期間（NaN）はノーポジ扱い
        warmup = slow_ma.isna()
        signal[warmup] = 0
        return signal

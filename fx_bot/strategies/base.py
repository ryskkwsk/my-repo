"""戦略の共通インターフェース。

戦略は「あとから差し替え可能」であることが重要。全ての戦略は Strategy を継承し、
generate_signals() で各バーの目標ポジション（1=ロング, -1=ショート, 0=ノーポジ）を
返す。この規約さえ守れば、バックテスト・ライブ双方で同じ戦略コードを使い回せる。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum

import pandas as pd


class Signal(IntEnum):
    LONG = 1
    FLAT = 0
    SHORT = -1


class Strategy(ABC):
    #: 表示・ログ用の名前
    name: str = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """OHLC の DataFrame を受け取り、各行の目標ポジションを Series で返す。

        返り値は df と同じ index を持ち、値は {1, 0, -1}。
        「そのバーの終値時点でどのポジションを持つべきか」を表す（未来を見ない）。
        """
        raise NotImplementedError

    def latest_signal(self, df: pd.DataFrame) -> Signal:
        """最新バーのシグナルだけを返す（ライブ運用ループ用）。"""
        signals = self.generate_signals(df)
        return Signal(int(signals.iloc[-1]))

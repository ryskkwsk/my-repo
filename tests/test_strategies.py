import numpy as np
import pandas as pd
import pytest

from fx_bot.strategies import MACrossStrategy
from fx_bot.strategies.base import Signal


def _df_from_close(close):
    close = pd.Series(close, dtype="float64")
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1}
    )


def test_fast_must_be_less_than_slow():
    with pytest.raises(ValueError):
        MACrossStrategy(fast=50, slow=20)


def test_warmup_is_flat():
    df = _df_from_close(np.linspace(100, 110, 30))
    sig = MACrossStrategy(fast=5, slow=10).generate_signals(df)
    # slow=10 が確定するまで（最初の9本）はノーポジ
    assert (sig.iloc[:9] == 0).all()


def test_uptrend_goes_long():
    # 単調増加 → 短期MAが長期MAより上 → ロング
    df = _df_from_close(np.linspace(100, 200, 100))
    sig = MACrossStrategy(fast=5, slow=20).generate_signals(df)
    assert sig.iloc[-1] == Signal.LONG


def test_downtrend_goes_short():
    df = _df_from_close(np.linspace(200, 100, 100))
    sig = MACrossStrategy(fast=5, slow=20).generate_signals(df)
    assert sig.iloc[-1] == Signal.SHORT


def test_no_short_when_disabled():
    df = _df_from_close(np.linspace(200, 100, 100))
    sig = MACrossStrategy(fast=5, slow=20, allow_short=False).generate_signals(df)
    assert sig.iloc[-1] == Signal.FLAT
    assert set(sig.unique()).issubset({0, 1})

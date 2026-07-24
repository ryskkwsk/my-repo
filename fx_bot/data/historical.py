"""ヒストリカルデータ取得。

- 認証情報があれば OANDA から実データを取得しローカルにキャッシュ。
- 無ければ合成データ（ランダムウォーク）を返すので、トークン発行前でも
  バックテストのパイプライン全体を動かして確認できる。
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_DIR = Path("data/cache")


def _cache_path(instrument: str, granularity: str, count: int) -> Path:
    return CACHE_DIR / f"{instrument}_{granularity}_{count}.csv"


def get_candles(
    instrument: str = "USD_JPY",
    granularity: str = "H1",
    count: int = 2000,
    use_cache: bool = True,
) -> pd.DataFrame:
    """OHLC の DataFrame を返す。

    列: [open, high, low, close, volume]、index は時刻(UTC)。
    認証情報が無い場合は合成データにフォールバックする。
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(instrument, granularity, count)

    if use_cache and path.exists():
        return pd.read_csv(path, index_col=0, parse_dates=True)

    from fx_bot.config import load_settings

    settings = load_settings()
    if settings.has_credentials:
        df = _fetch_from_oanda(settings, instrument, granularity, count)
        df.to_csv(path)
        return df

    # フォールバック: 合成データ
    print(
        "[data] OANDA 認証情報が無いため合成データを使用します "
        "（.env を設定すると実データを取得します）。"
    )
    return generate_synthetic_candles(instrument, granularity, count)


def _fetch_from_oanda(settings, instrument, granularity, count) -> pd.DataFrame:
    """OANDA v20 API からローソク足を取得する。"""
    from oandapyV20 import API
    from oandapyV20.endpoints.instruments import InstrumentsCandles

    client = API(access_token=settings.api_token, environment=settings.oanda_env)
    rows: list[dict] = []
    remaining = count
    params_to = None

    # OANDA は1リクエスト最大5000本。count が大きくてもページングで取得。
    while remaining > 0:
        batch = min(remaining, 5000)
        params = {"granularity": granularity, "count": batch, "price": "M"}
        if params_to:
            params["to"] = params_to
        req = InstrumentsCandles(instrument=instrument, params=params)
        client.request(req)
        candles = [c for c in req.response["candles"] if c["complete"]]
        if not candles:
            break
        for c in candles:
            mid = c["mid"]
            rows.append(
                {
                    "time": pd.to_datetime(c["time"]),
                    "open": float(mid["o"]),
                    "high": float(mid["h"]),
                    "low": float(mid["l"]),
                    "close": float(mid["c"]),
                    "volume": int(c["volume"]),
                }
            )
        remaining -= len(candles)
        params_to = candles[0]["time"]  # さらに過去へ遡る
        if len(candles) < batch:
            break

    df = pd.DataFrame(rows).drop_duplicates("time").sort_values("time")
    df = df.set_index("time")
    return df.tail(count)


def generate_synthetic_candles(
    instrument: str = "USD_JPY",
    granularity: str = "H1",
    count: int = 2000,
    seed: int = 42,
) -> pd.DataFrame:
    """再現可能な合成OHLCを生成する（テスト・デモ用）。

    トレンドと反転を含むランダムウォークなので、移動平均クロスの挙動確認に使える。
    """
    rng = np.random.default_rng(seed)
    start_price = 150.0 if instrument.upper().endswith("JPY") else 1.10
    vol = 0.05 if instrument.upper().endswith("JPY") else 0.0005

    # ゆるやかに変化するドリフトを重ねてトレンド/レンジを作る
    drift = np.cumsum(rng.normal(0, vol * 0.1, count))
    drift = drift - drift.mean()
    steps = rng.normal(0, vol, count) + drift * 0.02
    close = start_price + np.cumsum(steps)

    freq = {"M1": "1min", "M5": "5min", "M15": "15min", "H1": "1h",
            "H4": "4h", "D": "1D"}.get(granularity, "1h")
    idx = pd.date_range(end=pd.Timestamp.now("UTC").floor("min"),
                        periods=count, freq=freq, tz="UTC").tz_localize(None)

    open_ = np.empty(count)
    open_[0] = start_price
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) + np.abs(rng.normal(0, vol * 0.5, count))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, vol * 0.5, count))
    volume = rng.integers(500, 5000, count)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )

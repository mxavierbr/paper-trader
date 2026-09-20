import numpy as np
import pandas as pd

from indicators import add_indicators


def _fake_ohlcv(periods=60):
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, periods))
    high = close + np.abs(rng.normal(0, 1, periods))
    low = close - np.abs(rng.normal(0, 1, periods))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    volume = rng.integers(1000, 5000, periods)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def test_atr_column_exists_and_is_non_negative():
    df = add_indicators(_fake_ohlcv(), atr_period=14)
    assert "atr" in df.columns
    valid = df["atr"].dropna()
    assert len(valid) > 0
    assert (valid >= 0).all()


def test_atr_is_nan_before_enough_periods():
    df = add_indicators(_fake_ohlcv(), atr_period=14)
    assert df["atr"].iloc[:13].isna().all()
    assert not pd.isna(df["atr"].iloc[-1])

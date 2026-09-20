"""Indicadores técnicos: médias móveis, RSI, Bandas de Bollinger."""

import pandas as pd


def add_indicators(df: pd.DataFrame, fast=9, slow=21, rsi_period=14, bb_period=20, bb_std=2, atr_period=14):
    df = df.copy()

    # Médias móveis
    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Bandas de Bollinger
    mid = df["close"].rolling(bb_period).mean()
    std = df["close"].rolling(bb_period).std()
    df["bb_mid"] = mid
    df["bb_upper"] = mid + bb_std * std
    df["bb_lower"] = mid - bb_std * std

    # ATR (Average True Range) — volatilidade absoluta do ativo, usada
    # pela gestão de risco para dimensionar posição e distância de stop/alvo.
    prev_close = df["close"].shift(1)
    true_range = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(atr_period).mean()

    return df

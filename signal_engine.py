"""
Motor de sinal técnico (determinístico).

Regra: combina cruzamento de médias, RSI e posição nas Bandas de Bollinger.
Cada componente vota BUY / SELL / HOLD; o sinal final exige maioria.

A camada de IA (Claude API) entra como segundo filtro: só confirma o
sinal técnico se a leitura de contexto/notícias não contradisser.
Isso fica para a próxima etapa — aqui está a base determinística.
"""

import pandas as pd


def _vote_ma(row) -> str:
    if row["ma_fast"] > row["ma_slow"]:
        return "BUY"
    if row["ma_fast"] < row["ma_slow"]:
        return "SELL"
    return "HOLD"


def _vote_rsi(row) -> str:
    if row["rsi"] < 30:
        return "BUY"   # sobrevendido
    if row["rsi"] > 70:
        return "SELL"  # sobrecomprado
    return "HOLD"


def _vote_bb(row) -> str:
    if row["close"] <= row["bb_lower"]:
        return "BUY"
    if row["close"] >= row["bb_upper"]:
        return "SELL"
    return "HOLD"


def generate_signal(df: pd.DataFrame) -> dict:
    row = df.iloc[-1]
    if pd.isna(row[["ma_fast", "ma_slow", "rsi", "bb_upper", "bb_lower"]]).any():
        return {"signal": "HOLD", "reason": "dados insuficientes para todos os indicadores"}

    votes = {"ma": _vote_ma(row), "rsi": _vote_rsi(row), "bb": _vote_bb(row)}
    buy_votes = sum(1 for v in votes.values() if v == "BUY")
    sell_votes = sum(1 for v in votes.values() if v == "SELL")

    if buy_votes >= 2:
        signal = "BUY"
    elif sell_votes >= 2:
        signal = "SELL"
    else:
        signal = "HOLD"

    pct_change = round(((row["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"]) * 100, 2)

    return {
        "signal": signal,
        "price": round(float(row["close"]), 2),
        "pct_change": pct_change,
        "rsi": round(float(row["rsi"]), 1),
        "votes": votes,
        "timestamp": df.index[-1],
    }

"""
Métricas por ação calculadas sobre o histórico diário (já com indicadores):
variação por período e acerto histórico da regra de sinal.

Acerto histórico: a regra de sinal (signal_engine) é reaplicada dia a dia
no histórico. Conta só o primeiro dia de cada sequência de sinais iguais
(um sinal que dura 4 dias é 1 sinal, não 4). Um sinal de COMPRA acerta se
o preço está mais alto `horizon` pregões depois; VENDA acerta se está mais
baixo. Com o plano gratuito da brapi (3 meses de histórico), a amostra é
pequena — o painel mostra o número de sinais junto do percentual.
"""

import pandas as pd

from signal_engine import generate_signal

# Primeiro índice com todos os indicadores disponíveis (maior janela: 21).
WARMUP = 21


def pct(a: float, b: float) -> float | None:
    """Variação percentual de a para b."""
    if a is None or b is None or a == 0:
        return None
    return round((b / a - 1) * 100, 2)


def performance(df: pd.DataFrame) -> dict:
    close = df["close"]
    last = float(close.iloc[-1])

    def back(n):
        return pct(float(close.iloc[-1 - n]), last) if len(close) > n else None

    return {
        "var_5d": back(5),
        "var_21d": back(21),
        "var_periodo": pct(float(close.iloc[0]), last),
    }


def signal_track_record(df: pd.DataFrame, horizon: int = 5) -> dict:
    """Reaplica a regra de sinal no histórico e mede o acerto."""
    events = []
    prev = "HOLD"
    for i in range(WARMUP, len(df)):
        sig = generate_signal(df.iloc[: i + 1])["signal"]
        if sig != "HOLD" and sig != prev:
            events.append((i, sig))
        prev = sig

    marks, hits, evaluated, returns = [], 0, 0, []
    for i, sig in events:
        marks.append({"data": df.index[i].strftime("%Y-%m-%d"), "signal": sig,
                      "preco": round(float(df["close"].iloc[i]), 2)})
        if i + horizon >= len(df):
            continue  # ainda não deu tempo de avaliar
        entry, exit_ = float(df["close"].iloc[i]), float(df["close"].iloc[i + horizon])
        move = (exit_ / entry - 1) * 100
        directional = move if sig == "BUY" else -move
        evaluated += 1
        hits += directional > 0
        returns.append(directional)

    return {
        "horizonte_pregoes": horizon,
        "sinais": len(events),
        "avaliados": evaluated,
        "acertos": hits,
        "taxa_acerto": round(hits / evaluated * 100) if evaluated else None,
        "retorno_medio": round(sum(returns) / len(returns), 2) if returns else None,
        "marcacoes": marks,
    }

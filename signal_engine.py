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


def _media_rapida_subindo(df: pd.DataFrame) -> bool:
    """A média rápida virou pra cima na última barra — proxy de que o
    movimento recente ganhou fôlego (pra cima), não só que o preço mudou."""
    if len(df) < 2:
        return False
    return bool(df.iloc[-1]["ma_fast"] > df.iloc[-2]["ma_fast"])


def generate_signal(df: pd.DataFrame) -> dict:
    row = df.iloc[-1]
    if pd.isna(row[["ma_fast", "ma_slow", "rsi", "bb_upper", "bb_lower", "atr"]]).any():
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

    # Regra: preço baixo sozinho não é motivo de compra — só confirma se a
    # média rápida já virou pra cima (indício real de probabilidade de
    # crescimento). Sem isso, comprar na baixa é só "pegar faca caindo".
    # Regra espelhada: preço alto sozinho não é motivo de venda — só
    # confirma se a média rápida já parou de subir (indício de que a alta
    # bateu no teto), senão corta uma tendência que ainda pode continuar.
    motivo_veto = None
    media_subindo = _media_rapida_subindo(df)
    if signal == "BUY" and not media_subindo:
        signal = "HOLD"
        motivo_veto = "preço caiu, mas a média ainda não virou pra cima — sem confirmação de crescimento"
    elif signal == "SELL" and media_subindo:
        signal = "HOLD"
        motivo_veto = "preço subiu, mas a média ainda está em alta — sem confirmação de topo"

    prev_close = df.iloc[-2]["close"] if len(df) >= 2 else df.iloc[0]["close"]
    pct_change = round(((row["close"] - prev_close) / prev_close) * 100, 2)

    resultado = {
        "signal": signal,
        "price": round(float(row["close"]), 2),
        "pct_change": pct_change,
        "rsi": round(float(row["rsi"]), 1),
        "atr": round(float(row["atr"]), 4),
        "votes": votes,
        "timestamp": df.index[-1],
    }
    if motivo_veto:
        resultado["motivo_veto_tecnico"] = motivo_veto
    return resultado

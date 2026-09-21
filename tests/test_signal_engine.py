"""Testes do motor de sinal técnico, incluindo as regras de confirmação:
preço baixo só vira BUY se a média rápida já virou pra cima (probabilidade
de crescimento), e preço alto só vira SELL se a média já parou de subir
(topo de alta) — do contrário, vira HOLD com o motivo explicado.
"""

import pandas as pd

from signal_engine import generate_signal


def _make_df(prev_ma_fast, cur_ma_fast, ma_slow, rsi, bb_upper, bb_lower, atr=2.0, close=100.0):
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    return pd.DataFrame({
        "close": [close - 1, close],
        "ma_fast": [prev_ma_fast, cur_ma_fast],
        "ma_slow": [ma_slow, ma_slow],
        "rsi": [rsi, rsi],
        "bb_upper": [bb_upper, bb_upper],
        "bb_lower": [bb_lower, bb_lower],
        "atr": [atr, atr],
    }, index=idx)


def test_buy_confirmado_quando_media_rapida_vira_pra_cima():
    # ma_fast > ma_slow, rsi sobrevendido, close no fundo da banda -> 3 votos BUY
    # média rápida subindo (95 -> 96) confirma probabilidade de crescimento
    df = _make_df(prev_ma_fast=95, cur_ma_fast=96, ma_slow=90, rsi=25, bb_upper=110, bb_lower=100, close=100)
    resultado = generate_signal(df)
    assert resultado["signal"] == "BUY"
    assert "motivo_veto_tecnico" not in resultado


def test_buy_vetado_sem_confirmacao_de_crescimento():
    # mesmo cenário de preço baixo, mas média rápida ainda caindo (97 -> 96)
    df = _make_df(prev_ma_fast=97, cur_ma_fast=96, ma_slow=90, rsi=25, bb_upper=110, bb_lower=100, close=100)
    resultado = generate_signal(df)
    assert resultado["signal"] == "HOLD"
    assert "confirmação de crescimento" in resultado["motivo_veto_tecnico"]


def test_sell_confirmado_quando_media_rapida_para_de_subir():
    # ma_fast < ma_slow, rsi sobrecomprado, close no topo da banda -> 3 votos SELL
    # média rápida caindo (106 -> 105) confirma que a alta bateu no teto
    df = _make_df(prev_ma_fast=106, cur_ma_fast=105, ma_slow=110, rsi=75, bb_upper=100, bb_lower=90, close=100)
    resultado = generate_signal(df)
    assert resultado["signal"] == "SELL"
    assert "motivo_veto_tecnico" not in resultado


def test_sell_vetado_sem_confirmacao_de_topo():
    # mesmo cenário de preço alto, mas média rápida ainda subindo (104 -> 105)
    df = _make_df(prev_ma_fast=104, cur_ma_fast=105, ma_slow=110, rsi=75, bb_upper=100, bb_lower=90, close=100)
    resultado = generate_signal(df)
    assert resultado["signal"] == "HOLD"
    assert "confirmação de topo" in resultado["motivo_veto_tecnico"]


def test_narracao_explica_o_veto_tecnico():
    from narrator import narrate

    sinal = {
        "signal": "HOLD", "symbol": "PETR4", "price": 100.0, "rsi": 25.0,
        "motivo_veto_tecnico": "preço caiu, mas a média ainda não virou pra cima — sem confirmação de crescimento",
    }
    msg = narrate(sinal)
    assert "Maurício" in msg
    assert sinal["motivo_veto_tecnico"] in msg

"""Testes da camada de gestão de risco (risk.py)."""

from datetime import date, timedelta

import pytest

from risk import RiskConfig, GestorDeRisco


def make_gestor(**overrides) -> GestorDeRisco:
    config = RiskConfig(**overrides)
    return GestorDeRisco(config, patrimonio_inicial=100_000.0)


# ---------------------------------------------------------------------
# Dimensionamento pelo risco até o stop
# ---------------------------------------------------------------------

def test_avaliar_entrada_dimensiona_pelo_risco():
    # tetos de exposição bem folgados pra isolar o dimensionamento pelo risco
    gestor = make_gestor(exposicao_maxima_ativo=100, exposicao_maxima_setor=100,
                          exposicao_maxima_total=100)
    # patrimônio 100k, risco 1% => 1000 de risco financeiro
    # preco 100, atr 2 => stop = 100 - 2*2 = 96, risco/unidade = 4
    # qty esperado pelo risco = 1000/4 = 250
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=5_000_000)
    assert avaliacao["aprovado"] is True
    assert avaliacao["qty"] == 250
    assert avaliacao["stop"] == pytest.approx(96.0)
    assert avaliacao["alvo"] == pytest.approx(106.0)
    assert avaliacao["relacao_rr"] == pytest.approx(1.5)


def test_relacao_risco_retorno_abaixo_do_minimo_e_recusada():
    # mult_alvo_atr/mult_stop_atr = 1.0/2.0 = 0.5 < 1.5 mínimo
    gestor = make_gestor(mult_stop_atr=2.0, mult_alvo_atr=1.0)
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=5_000_000)
    assert avaliacao["aprovado"] is False
    assert "risco/retorno" in avaliacao["motivo"]


def test_atr_invalido_e_recusado():
    gestor = make_gestor()
    assert gestor.avaliar_entrada("PETR4", "s", preco=100.0, atr=0.0)["aprovado"] is False
    assert gestor.avaliar_entrada("PETR4", "s", preco=100.0, atr=None)["aprovado"] is False


# ---------------------------------------------------------------------
# Tetos de exposição e liquidez
# ---------------------------------------------------------------------

def test_teto_exposicao_maxima_por_ativo():
    # exposição máxima por ativo 20% de 100k = 20.000; preco 100 => no máx 200 ações
    # risco por operação permitiria 250 (ver teste acima) — o teto de ativo deve prevalecer
    gestor = make_gestor(exposicao_maxima_ativo=20.0)
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=50_000_000)
    assert avaliacao["aprovado"] is True
    assert avaliacao["qty"] == 200
    assert avaliacao["teto_limitante"] == "exposição máxima por ativo"


def test_teto_exposicao_maxima_por_setor():
    gestor = make_gestor(exposicao_maxima_setor=5.0, max_posicoes=10)
    # 5% de 100k = 5.000 => no máx 50 ações a 100
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=50_000_000)
    assert avaliacao["qty"] == 50
    assert avaliacao["teto_limitante"] == "exposição máxima por setor"


def test_teto_exposicao_maxima_total():
    gestor = make_gestor(exposicao_maxima_total=5.0, max_posicoes=10)
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=50_000_000)
    assert avaliacao["qty"] == 50
    assert avaliacao["teto_limitante"] == "exposição máxima total"


def test_liquidez_insuficiente_recusa_entrada():
    gestor = make_gestor()
    avaliacao = gestor.avaliar_entrada("MICRO3", "small_cap", preco=10.0, atr=0.5,
                                        volume_financeiro_medio=500_000)
    assert avaliacao["aprovado"] is False
    assert "liquidez" in avaliacao["motivo"]


def test_participacao_maxima_volume_limita_quantidade():
    gestor = make_gestor(participacao_maxima_volume=1.0)
    # volume financeiro médio 2 milhões, 1% = 20.000 => no máx 200 ações a 100
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=2_000_000)
    assert avaliacao["qty"] <= 200


def test_max_posicoes_simultaneas():
    gestor = make_gestor(max_posicoes=1, exposicao_maxima_ativo=100, exposicao_maxima_setor=100,
                          exposicao_maxima_total=100)
    a1 = gestor.avaliar_entrada("A", "s1", preco=10.0, atr=0.2, volume_financeiro_medio=5_000_000)
    gestor.abrir_posicao("A", "s1", a1["qty"], 10.0, a1["stop"], a1["alvo"])

    a2 = gestor.avaliar_entrada("B", "s2", preco=10.0, atr=0.2, volume_financeiro_medio=5_000_000)
    assert a2["aprovado"] is False
    assert "posições simultâneas" in a2["motivo"]


def test_caixa_insuficiente_limita_quantidade():
    # tetos de risco/exposição bem folgados pra isolar o teto de caixa —
    # como patrimônio = caixa (sem posições abertas), risco% e exposição%
    # também encolhem junto com o caixa, então precisam ficar bem acima
    # de 100% pra não virarem o teto que efetivamente limita a compra.
    gestor = make_gestor(risco_por_operacao=1000, exposicao_maxima_ativo=1_000_000,
                          exposicao_maxima_setor=1_000_000, exposicao_maxima_total=1_000_000)
    gestor.caixa = 500.0
    avaliacao = gestor.avaliar_entrada("PETR4", "petroleo", preco=100.0, atr=2.0,
                                        volume_financeiro_medio=5_000_000)
    assert avaliacao["aprovado"] is True
    assert avaliacao["qty"] <= 5
    assert avaliacao["teto_limitante"] == "caixa disponível"


# ---------------------------------------------------------------------
# Trailing stop e saídas
# ---------------------------------------------------------------------

def test_trailing_stop_so_sobe_nunca_desce():
    gestor = make_gestor()
    gestor.abrir_posicao("PETR4", "petroleo", 100, 100.0, stop=96.0, alvo=106.0)

    gestor.atualizar_trailing("PETR4", 110.0, atr=2.0)
    stop_apos_alta = gestor.posicoes["PETR4"].stop
    assert stop_apos_alta > 96.0  # subiu

    gestor.atualizar_trailing("PETR4", 105.0, atr=2.0)  # preço recuou
    assert gestor.posicoes["PETR4"].stop == stop_apos_alta  # stop não desceu


def test_checar_saida_stop_e_alvo():
    gestor = make_gestor()
    gestor.abrir_posicao("PETR4", "petroleo", 100, 100.0, stop=96.0, alvo=106.0)

    assert gestor.checar_saida("PETR4", 96.0) == "STOP"
    assert gestor.checar_saida("PETR4", 106.0) == "ALVO"
    assert gestor.checar_saida("PETR4", 100.0) is None


def test_processar_precos_fecha_posicao_no_stop():
    gestor = make_gestor()
    gestor.abrir_posicao("PETR4", "petroleo", 100, 100.0, stop=96.0, alvo=106.0)

    eventos = gestor.processar_precos({"PETR4": 95.0}, {"PETR4": 2.0})
    assert len(eventos) == 1
    assert eventos[0]["motivo"] == "STOP"
    assert "PETR4" not in gestor.posicoes


# ---------------------------------------------------------------------
# Custo de operação
# ---------------------------------------------------------------------

def test_custo_descontado_na_compra_e_na_venda():
    gestor = make_gestor(custo_operacao_pct=0.05)
    caixa_antes = gestor.caixa
    gestor.abrir_posicao("PETR4", "petroleo", 100, 100.0, stop=96.0, alvo=106.0)

    custo_compra_esperado = 100 * 100 * 0.05 / 100
    assert gestor.caixa == pytest.approx(caixa_antes - (100 * 100) - custo_compra_esperado)

    registro = gestor.fechar_posicao("PETR4", 106.0, "ALVO")
    custo_venda_esperado = 106 * 100 * 0.05 / 100
    pnl_esperado = (106 - 100) * 100 - custo_compra_esperado - custo_venda_esperado
    assert registro["pnl"] == pytest.approx(pnl_esperado)


# ---------------------------------------------------------------------
# Circuit breakers
# ---------------------------------------------------------------------

def test_perda_maxima_diaria_bloqueia_novas_entradas():
    gestor = make_gestor(perda_maxima_diaria=3.0)
    gestor.abrir_posicao("PETR4", "petroleo", 1000, 100.0, stop=50.0, alvo=200.0)

    # queda de preço gera prejuízo realizado > 3% do patrimônio de abertura do dia
    gestor.processar_precos({"PETR4": 50.0}, {"PETR4": 2.0})

    assert gestor.bloqueio_diario is True
    avaliacao = gestor.avaliar_entrada("VALE3", "mineracao", preco=50.0, atr=1.0,
                                        volume_financeiro_medio=5_000_000)
    assert avaliacao["aprovado"] is False
    assert "diária" in avaliacao["motivo"]


def test_bloqueio_diario_reseta_no_dia_seguinte():
    gestor = make_gestor()
    gestor.bloqueio_diario = True
    gestor._data_referencia = date.today() - timedelta(days=1)

    gestor.processar_precos({}, {})
    assert gestor.bloqueio_diario is False


def test_drawdown_maximo_bloqueia_ate_reset_manual():
    gestor = make_gestor(drawdown_maximo=10.0)
    # stop e alvo bem fora do range de preço testado, pra isolar o
    # drawdown por marcação a mercado sem disparar saída por stop/alvo
    gestor.abrir_posicao("PETR4", "petroleo", 500, 100.0, stop=1.0, alvo=1000.0)
    gestor.processar_precos({"PETR4": 100.0})
    assert gestor.patrimonio_maximo >= 100_000.0

    # queda de preço reduz patrimônio > 10% do pico, sem realizar a perda
    gestor.processar_precos({"PETR4": 80.0})
    assert gestor.pnl_dia == 0.0  # nenhuma posição foi fechada
    assert gestor.bloqueio_drawdown is True
    assert gestor.bloqueio_diario is False

    avaliacao = gestor.avaliar_entrada("VALE3", "mineracao", preco=50.0, atr=1.0,
                                        volume_financeiro_medio=5_000_000)
    assert avaliacao["aprovado"] is False
    assert "drawdown" in avaliacao["motivo"]

    # não desbloqueia sozinho no dia seguinte
    gestor._data_referencia = date.today() - timedelta(days=1)
    gestor.processar_precos({"PETR4": 80.0})
    assert gestor.bloqueio_drawdown is True

    gestor.resetar_drawdown()
    assert gestor.bloqueio_drawdown is False


def test_status_reporta_campos_esperados():
    gestor = make_gestor()
    gestor.abrir_posicao("PETR4", "petroleo", 100, 100.0, stop=96.0, alvo=106.0)
    status = gestor.status()

    for campo in ("patrimonio", "caixa", "exposicao_total", "exposicao_total_pct",
                  "posicoes_abertas", "num_posicoes_abertas", "resultado_do_dia",
                  "drawdown_atual_pct", "bloqueio_perda_diaria", "bloqueio_drawdown",
                  "bloqueado"):
        assert campo in status
    assert status["num_posicoes_abertas"] == 1

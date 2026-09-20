"""Testes de integração leves: sinal -> ATR -> gestão de risco -> portfólio.

Usa apenas o mercado 'intl', que no data_source.py roteia para
MockDataSource (sem chamada de rede), pra manter o teste rápido e
determinístico.
"""

from main import scan_market, process_signals, ranquear_oportunidades_compra
from paper_portfolio import PaperPortfolio
from risk import RiskConfig, GestorDeRisco


def test_process_signals_nao_quebra_e_produz_status_coerente():
    portfolio = PaperPortfolio()
    gestor = GestorDeRisco(RiskConfig())

    all_results = scan_market("intl")
    assert len(all_results) > 0
    assert all("atr" in r for r in all_results)

    process_signals(all_results, gestor, portfolio)

    status = gestor.status()
    assert status["patrimonio"] > 0
    assert status["num_posicoes_abertas"] == len(status["posicoes_abertas"])
    assert status["num_posicoes_abertas"] <= gestor.config.max_posicoes


def test_entrada_recusada_gera_motivo_no_sinal_e_narracao():
    """Sinal sintético controlado (não depende do resultado aleatório do
    scan_market) para garantir a recusa e testar a mensagem ao Maurício."""
    portfolio = PaperPortfolio()
    # patrimônio minúsculo -> qualquer BUY deve ser recusado pelo risco
    gestor = GestorDeRisco(RiskConfig(), patrimonio_inicial=10.0)
    gestor.caixa = 10.0

    sinal_buy = {
        "signal": "BUY", "symbol": "AAPL", "setor": "dolar_eua", "price": 230.0,
        "pct_change": 1.2, "rsi": 25.0, "atr": 3.0, "volume_financeiro": 50_000_000,
        "votes": {}, "timestamp": "2024-01-01T00:00:00", "ai_reasoning": None,
    }
    all_results = [sinal_buy]
    process_signals(all_results, gestor, portfolio)

    assert sinal_buy["signal"] == "BUY"
    assert sinal_buy.get("risco_motivo")
    assert "AAPL" not in gestor.posicoes

    from narrator import narrate
    msg = narrate(sinal_buy)
    assert "Maurício" in msg
    assert sinal_buy["risco_motivo"] in msg


def _sinal_buy(symbol="AAPL", price=230.0, atr=3.0, timestamp="2024-01-01T00:00:00"):
    return {
        "signal": "BUY", "symbol": symbol, "setor": "dolar_eua", "price": price,
        "pct_change": 1.2, "rsi": 25.0, "atr": atr, "volume_financeiro": 50_000_000,
        "votes": {}, "timestamp": timestamp, "ai_reasoning": None,
    }


def test_entrada_aprovada_aparece_no_ranking_de_oportunidades():
    portfolio = PaperPortfolio()
    gestor = GestorDeRisco(RiskConfig())

    all_results = [_sinal_buy()]
    process_signals(all_results, gestor, portfolio)

    assert all_results[0].get("avaliacao_risco")
    assert "AAPL" in gestor.posicoes

    oportunidades = ranquear_oportunidades_compra(all_results)
    assert len(oportunidades) == 1
    assert oportunidades[0]["symbol"] == "AAPL"


def test_reforco_de_posicao_e_sinalizado_na_narracao():
    portfolio = PaperPortfolio()
    gestor = GestorDeRisco(RiskConfig())

    process_signals([_sinal_buy(timestamp="2024-01-01T00:00:00")], gestor, portfolio)
    qty_apos_primeira_compra = gestor.posicoes["AAPL"].qty

    segundo_sinal = [_sinal_buy(price=225.0, timestamp="2024-01-01T00:05:00")]
    process_signals(segundo_sinal, gestor, portfolio)

    assert segundo_sinal[0]["reforco_posicao"] is True
    assert gestor.posicoes["AAPL"].qty > qty_apos_primeira_compra

    from narrator import narrate
    msg = narrate(segundo_sinal[0])
    assert "já tem AAPL" in msg


def test_stop_atingido_gera_alerta_de_venda():
    portfolio = PaperPortfolio()
    gestor = GestorDeRisco(RiskConfig())

    process_signals([_sinal_buy(price=230.0, atr=3.0)], gestor, portfolio)
    stop = gestor.posicoes["AAPL"].stop

    sinal_preco_no_stop = _sinal_buy(price=stop, timestamp="2024-01-01T00:05:00")
    sinal_preco_no_stop["signal"] = "HOLD"
    eventos = process_signals([sinal_preco_no_stop], gestor, portfolio)

    assert len(eventos) == 1
    assert eventos[0]["symbol"] == "AAPL"
    assert eventos[0]["motivo"] == "STOP"
    assert "AAPL" not in gestor.posicoes

    from narrator import narrate_saida
    msg = narrate_saida(eventos[0])
    assert "Maurício" in msg
    assert "vender AAPL" in msg

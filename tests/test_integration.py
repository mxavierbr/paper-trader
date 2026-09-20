"""Testes de integração leves: sinal -> ATR -> gestão de risco -> portfólio.

Usa apenas o mercado 'intl', que no data_source.py roteia para
MockDataSource (sem chamada de rede), pra manter o teste rápido e
determinístico.
"""

from main import scan_market, process_signals
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

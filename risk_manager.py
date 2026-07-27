"""
Gestão de risco — a camada que decide QUANTO operar e QUANDO sair,
separada do sinal que decide O QUE operar (BUY/SELL).

Sem isso, o motor de sinal pode estar certo e o app ainda perder dinheiro
por operar tamanho errado ou não ter saída definida.
"""

from dataclasses import dataclass


@dataclass
class RiskConfig:
    capital_total: float = 100_000.0
    risco_por_trade_pct: float = 1.0     # % do capital que pode virar prejuízo em 1 trade
    exposicao_maxima_pct: float = 30.0   # % do capital em posições abertas ao mesmo tempo
    stop_loss_pct: float = 2.0           # distância do stop em relação ao preço de entrada
    take_profit_pct: float = 4.0         # distância do alvo (mínimo 2:1 reward/risk)


def calc_position_size(price: float, rsi_volatility_proxy: float, config: RiskConfig) -> dict:
    """
    Calcula quantos contratos/ações operar, baseado em quanto capital pode
    ser arriscado no trade e na distância até o stop.

    rsi_volatility_proxy: aqui usamos a distância do RSI a 50 como proxy
    simples de "quão esticado" o ativo está — na versão real, trocar por
    ATR (Average True Range), que é o padrão de mercado pra medir
    volatilidade e dimensionar posição.
    """
    risco_financeiro = config.capital_total * (config.risco_por_trade_pct / 100)
    stop_distance = price * (config.stop_loss_pct / 100)

    qty = int(risco_financeiro / stop_distance) if stop_distance > 0 else 0

    return {
        "qty": max(qty, 0),
        "stop_loss_price": round(price * (1 - config.stop_loss_pct / 100), 2),
        "take_profit_price": round(price * (1 + config.take_profit_pct / 100), 2),
        "risco_financeiro": round(risco_financeiro, 2),
    }


def check_exposure_limit(portfolio_value_in_positions: float, config: RiskConfig) -> bool:
    """Retorna True se AINDA HÁ espaço para abrir mais uma posição sem
    estourar o limite de exposição total definido."""
    limite = config.capital_total * (config.exposicao_maxima_pct / 100)
    return portfolio_value_in_positions < limite

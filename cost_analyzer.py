"""
Custo de operação — desconta IR de day trade (20% sobre lucro, sem
isenção de faixa) e corretagem, pra saber se o trade vale a pena depois
de custos. Sem isso, o motor pode marcar "lucro" que na prática vira
prejuízo líquido em operações pequenas.
"""

IR_DAY_TRADE_PCT = 20.0
# Simplificação: day trade não tem isenção de faixa (diferente de swing
# trade em ações, que tem isenção até R$20mil/mês em vendas). Regras
# variam por tipo de ativo (ação, futuro, câmbio) e mudam por lei — não
# usar isso como cálculo fiscal definitivo, só como filtro de decisão.


def net_result(gross_pnl: float, corretagem_por_operacao: float = 0.0) -> dict:
    custos = corretagem_por_operacao * 2  # entrada + saída
    lucro_apos_corretagem = gross_pnl - custos
    ir = max(lucro_apos_corretagem, 0) * (IR_DAY_TRADE_PCT / 100)
    liquido = lucro_apos_corretagem - ir

    return {
        "bruto": round(gross_pnl, 2),
        "corretagem": round(custos, 2),
        "ir_devido": round(ir, 2),
        "liquido": round(liquido, 2),
        "vale_a_pena": liquido > 0,
    }


def min_move_to_profit(price: float, corretagem_por_operacao: float = 0.0) -> float:
    """Variação mínima de preço necessária pra cobrir corretagem + IR
    (dá uma noção de qual sinal é 'ruído' demais pra valer a pena)."""
    custos = corretagem_por_operacao * 2
    # aproximação: lucro bruto precisa cobrir custo / (1 - IR%)
    lucro_bruto_necessario = custos / (1 - IR_DAY_TRADE_PCT / 100)
    return round(lucro_bruto_necessario, 2)

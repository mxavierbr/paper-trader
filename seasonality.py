"""
Sazonalidade de commodities agrícolas — padrão de safra/entressafra que
historicamente pressiona preço. Isso é conhecimento de domínio da Jox
aplicado ao motor de sinal: um fator que os traders puramente técnicos
não costumam ter.

Simplificado aqui como calendário fixo por mês (hemisfério norte, onde
fica o CBOT). Em produção, cruzar com dados reais de safra (USDA WASDE,
CONAB) em vez de regra fixa — a safra pode atrasar/antecipar por clima.
"""

# mês -> viés sazonal típico (não é garantia, é tendência histórica)
CORN_SEASONAL_BIAS = {
    1: "neutro", 2: "neutro", 3: "pressão de baixa (plantio se aproxima, menos incerteza)",
    4: "pressão de baixa (plantio em curso)", 5: "volátil (clima de plantio define prêmio de risco)",
    6: "volátil (clima de desenvolvimento — polinização)", 7: "pico de volatilidade (polinização, safra EUA)",
    8: "tendência de baixa (colheita se aproxima, oferta maior)",
    9: "pressão de baixa (colheita)", 10: "pressão de baixa (colheita em pico)",
    11: "estabilização pós-colheita", 12: "neutro",
}


def get_seasonal_bias(symbol: str, month: int) -> str | None:
    if symbol == "ZCFUT":
        return CORN_SEASONAL_BIAS.get(month)
    return None

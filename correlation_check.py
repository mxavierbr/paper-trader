"""
Correlação entre ativos — se várias posições abertas na prática são a
mesma aposta (ex: WDOFUT + ESFUT + AAPL comprados = tudo "dólar forte/
mercado americano em alta"), o portfólio não está diversificado mesmo
tendo vários símbolos.
"""

# Grupos de correlação conhecida — simplificado; em produção calcular
# correlação real a partir do histórico de preços (ex: pandas .corr())
CORRELATION_GROUPS = {
    "dolar_eua": {"WDOFUT", "ESFUT", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "KO", "XOM"},
    "indice_br": {"WINFUT", "VALE3", "ITUB4", "BBDC4", "BBAS3", "ABEV3", "WEGE3"},
    "agro": {"ZCFUT", "SLCE3", "AGRO3", "TTEN3", "SOJA3", "SMTO3", "JALL3", "RAIZ4",
             "CAML3", "VITT3", "KEPL3", "MBRF3", "BEEF3", "JBSS32", "SUZB3", "KLBN11", "RAIL3"},
}


def group_of(symbol: str) -> str | None:
    for group, symbols in CORRELATION_GROUPS.items():
        if symbol in symbols:
            return group
    return None


def check_correlation_limit(symbol: str, open_positions: dict, max_por_grupo: int = 2) -> bool:
    """Retorna True se AINDA HÁ espaço pra abrir posição nesse grupo de
    correlação sem concentrar demais a mesma aposta."""
    grupo = group_of(symbol)
    if grupo is None:
        return True

    abertas_no_grupo = sum(
        1 for s, p in open_positions.items()
        if p.qty > 0 and group_of(s) == grupo
    )
    return abertas_no_grupo < max_por_grupo

"""Filtro de liquidez — um sinal tecnicamente perfeito em ativo pouco
negociado pode não ser executável no preço esperado (slippage alto)."""


def has_enough_liquidity(df, min_avg_volume: float = 5000) -> bool:
    avg_volume = df["volume"].tail(20).mean()
    return avg_volume >= min_avg_volume

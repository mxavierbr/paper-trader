"""
Backtest — roda o motor técnico contra uma série histórica e mede taxa
de acerto e drawdown. Essencial antes de confiar no sinal em paper
trading real (e mais ainda antes de execução real).

Nota: com MockDataSource (dados sintéticos aleatórios), o resultado do
backtest não tem valor preditivo — serve só para validar que a mecânica
funciona. Só fica útil de verdade com histórico real (2+ anos) via
Nelogica/brapi/IB.
"""

from indicators import add_indicators
from signal_engine import generate_signal


def run_backtest(source, symbol: str, total_periods: int = 500, window: int = 200) -> dict:
    full_df = source.get_ohlcv(symbol, periods=total_periods)

    trades = []
    open_price = None

    for i in range(window, total_periods):
        window_df = add_indicators(full_df.iloc[i - window:i])
        signal = generate_signal(window_df)

        if signal["signal"] == "BUY" and open_price is None:
            open_price = signal["price"]
        elif signal["signal"] == "SELL" and open_price is not None:
            trades.append(signal["price"] - open_price)
            open_price = None

    if not trades:
        return {"symbol": symbol, "trades": 0, "win_rate": None, "max_drawdown": None}

    wins = sum(1 for t in trades if t > 0)
    win_rate = round(wins / len(trades) * 100, 1)

    equity = []
    running = 0
    for t in trades:
        running += t
        equity.append(running)
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        max_dd = min(max_dd, e - peak)

    return {
        "symbol": symbol,
        "trades": len(trades),
        "win_rate": win_rate,
        "resultado_acumulado": round(sum(trades), 2),
        "max_drawdown": round(max_dd, 2),
    }

from datetime import datetime

from data_source import get_data_source, get_universe, MockDataSource
from indicators import add_indicators
from signal_engine import generate_signal
from paper_portfolio import PaperPortfolio
from narrator import narrate
from news_context import get_news_source
from fundamentals import get_fundamentals_source
from ai_layer import refine_signal
from liquidity_filter import has_enough_liquidity
from correlation_check import check_correlation_limit
from cost_analyzer import net_result
from event_calendar import get_event_calendar
from seasonality import get_seasonal_bias


def scan_market(market: str) -> list:
    """Varre todo o universo de um mercado, calcula indicadores, sinal
    técnico, filtra liquidez/eventos e refina com a camada de IA
    (notícias + fundamentos + sazonalidade)."""
    news_source = get_news_source()
    fundamentals_source = get_fundamentals_source()
    calendar = get_event_calendar()
    month = datetime.now().month
    results = []

    for symbol in get_universe(market):
        source = get_data_source(symbol)
        try:
            raw_df = source.get_ohlcv(symbol, periods=200)
        except (NotImplementedError, RuntimeError) as e:
            raw_df = MockDataSource().get_ohlcv(symbol, periods=200)
            print(f"[aviso] {symbol}: fonte real indisponível ({e}) — usando dado simulado")

        if not has_enough_liquidity(raw_df):
            continue  # ignora ativo pouco líquido — sinal não seria executável direito

        df = add_indicators(raw_df)
        signal = generate_signal(df)
        signal["symbol"] = symbol

        event = calendar.has_upcoming_event(symbol)
        if event:
            signal["signal"] = "HOLD"
            signal["ai_reasoning"] = f"evento de alta volatilidade próximo ({event}) — operação pausada"
            results.append(signal)
            continue

        headlines = news_source.get_recent_headlines(symbol)
        fundamentals = fundamentals_source.get_fundamentals(symbol)
        bias = get_seasonal_bias(symbol, month)
        if bias:
            fundamentals = {**fundamentals, "vies_sazonal_do_mes": bias}

        signal = refine_signal(signal, headlines, fundamentals)
        results.append(signal)

    return results


def run():
    portfolio = PaperPortfolio()
    all_results = scan_market("b3") + scan_market("intl")

    for r in all_results:
        if r["signal"] == "HOLD":
            continue
        if not check_correlation_limit(r["symbol"], portfolio.positions):
            r["signal"] = "HOLD"
            r["ai_reasoning"] = "bloqueado por concentração — já há posições correlacionadas abertas"
            continue
        portfolio.apply_signal(r["symbol"], r)

    ranked = sorted(all_results, key=lambda r: r["pct_change"], reverse=True)

    print(f"=== SCANNER DE MERCADO — {len(all_results)} ativos líquidos (paper trading) ===\n")

    print("--- Top 5 maiores ALTAS ---")
    for r in ranked[:5]:
        print(f"{r['symbol']:8s} {r['pct_change']:+6.2f}%  sinal={r['signal']:4s}  RSI={r['rsi']}")

    print("\n--- Top 5 maiores QUEDAS ---")
    for r in ranked[-5:][::-1]:
        print(f"{r['symbol']:8s} {r['pct_change']:+6.2f}%  sinal={r['signal']:4s}  RSI={r['rsi']}")

    signals = [r for r in all_results if r["signal"] != "HOLD"]
    print(f"\n--- Alertas ({len(signals)}) ---")
    for r in signals:
        print(narrate(r))

    print("\n=== RESUMO DO PORTFÓLIO SIMULADO ===")
    summary = portfolio.summary()
    print(summary)

    if portfolio.trade_log:
        last_trade = portfolio.trade_log[-1]
        if last_trade["action"] == "SELL":
            custo = net_result(last_trade["realized_pnl"], corretagem_por_operacao=5.0)
            print(f"\nÚltimo trade fechado após custos (IR + corretagem): {custo}")


if __name__ == "__main__":
    run()

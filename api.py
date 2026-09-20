"""
API do Paper Trader — expõe o pipeline (scan_market + portfólio) como
endpoint HTTP, pro dashboard.html consultar.

Rodar localmente:
  pip install fastapi uvicorn
  uvicorn api:app --host 0.0.0.0 --port 8000

Endpoints:
  GET /api/scan  -> mesmo formato JSON que o dashboard.html já espera
  GET /risco     -> status da gestão de risco (patrimônio, exposição,
                     posições abertas, resultado do dia, drawdown, bloqueios)

O estado da carteira (posições, caixa, resultado do dia, bloqueios) é
persistido no Supabase (store.py) — sobrevive a reinícios do backend no
Render. Sem SUPABASE_URL/SUPABASE_KEY configuradas, segue funcionando
normalmente, só que em memória (reseta a cada reinício).
"""

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main import scan_market, process_signals, ranquear_oportunidades_compra
from paper_portfolio import PaperPortfolio
from narrator import narrate, narrate_saida
from risk import RiskConfig, GestorDeRisco
import store

app = FastAPI(title="Paper Trader API")

# CORS liberado geral pra simplificar o protótipo. Em produção, restringir
# allow_origins pro domínio real do painel hospedado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Estado do processo — precisa persistir entre requisições pro circuit
# breaker de perda diária/drawdown e as posições abertas fazerem sentido.
# Hidratado do Supabase no start (se configurado) pra sobreviver a deploys.
portfolio = PaperPortfolio()
gestor_risco = GestorDeRisco(RiskConfig())
store.carregar_estado(gestor_risco)


@app.get("/api/scan")
def scan():
    all_results = scan_market("b3") + scan_market("intl")

    trades_antes = len(portfolio.trade_log)
    eventos_saida = process_signals(all_results, gestor_risco, portfolio)
    trades_novos = portfolio.trade_log[trades_antes:]

    store.registrar_trades(trades_novos)
    store.salvar_estado(gestor_risco)

    ranked = sorted(all_results, key=lambda r: r["pct_change"], reverse=True)
    signals = [r for r in all_results if r["signal"] != "HOLD"]
    oportunidades = ranquear_oportunidades_compra(all_results)

    return {
        "atualizado_em": datetime.now().isoformat(),
        "total_ativos": len(all_results),
        "top_altas": [
            {"symbol": r["symbol"], "pct_change": r["pct_change"], "price": r["price"]}
            for r in ranked[:6]
        ],
        "top_quedas": [
            {"symbol": r["symbol"], "pct_change": r["pct_change"], "price": r["price"]}
            for r in ranked[-6:][::-1]
        ],
        "oportunidades_compra": [
            {"symbol": r["symbol"], "price": r["price"],
             "relacao_rr": r["avaliacao_risco"]["relacao_rr"],
             "stop": r["avaliacao_risco"]["stop"], "alvo": r["avaliacao_risco"]["alvo"],
             "mensagem": narrate(r)}
            for r in oportunidades
        ],
        "alertas": [
            {"symbol": r["symbol"], "signal": r["signal"], "price": r["price"],
             "mensagem": narrate(r)}
            for r in signals
        ],
        "alertas_venda": [
            {"symbol": e["symbol"], "motivo": e["motivo"], "preco_saida": e["preco_saida"],
             "pnl": e["pnl"], "mensagem": narrate_saida(e)}
            for e in eventos_saida
        ],
        "portfolio": portfolio.summary(),
    }


@app.get("/risco")
def risco():
    return gestor_risco.status()


@app.get("/api/health")
def health():
    return {"status": "ok"}

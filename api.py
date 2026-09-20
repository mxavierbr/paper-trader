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
"""

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main import scan_market, process_signals
from paper_portfolio import PaperPortfolio
from narrator import narrate
from risk import RiskConfig, GestorDeRisco

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
portfolio = PaperPortfolio()
gestor_risco = GestorDeRisco(RiskConfig())


@app.get("/api/scan")
def scan():
    all_results = scan_market("b3") + scan_market("intl")
    process_signals(all_results, gestor_risco, portfolio)

    ranked = sorted(all_results, key=lambda r: r["pct_change"], reverse=True)
    signals = [r for r in all_results if r["signal"] != "HOLD"]

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
        "alertas": [
            {"symbol": r["symbol"], "signal": r["signal"], "price": r["price"],
             "mensagem": narrate(r)}
            for r in signals
        ],
        "portfolio": portfolio.summary(),
    }


@app.get("/risco")
def risco():
    return gestor_risco.status()


@app.get("/api/health")
def health():
    return {"status": "ok"}

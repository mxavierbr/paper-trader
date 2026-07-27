"""
API do Paper Trader — expõe o pipeline (scan_market + portfólio) como
endpoint HTTP, pro dashboard.html consultar.

Rodar localmente:
  pip install fastapi uvicorn
  uvicorn api:app --host 0.0.0.0 --port 8000

Endpoint principal:
  GET /api/scan  -> mesmo formato JSON que o dashboard.html já espera
"""

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main import scan_market
from paper_portfolio import PaperPortfolio
from correlation_check import check_correlation_limit
from narrator import narrate

app = FastAPI(title="Paper Trader API")

# CORS liberado geral pra simplificar o protótipo. Em produção, restringir
# allow_origins pro domínio real do painel hospedado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/scan")
def scan():
    portfolio = PaperPortfolio()
    all_results = scan_market("b3") + scan_market("intl")

    for r in all_results:
        if r["signal"] == "HOLD":
            continue
        if not check_correlation_limit(r["symbol"], portfolio.positions):
            r["signal"] = "HOLD"
            continue
        portfolio.apply_signal(r["symbol"], r)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}

"""
API do Paper Trader — expõe o pipeline (scan_market + portfólio) como
endpoint HTTP, pro dashboard.html consultar.

Rodar localmente:
  pip install fastapi uvicorn
  uvicorn api:app --host 0.0.0.0 --port 8000

Endpoint principal:
  GET /api/scan  -> mesmo formato JSON que o dashboard.html já espera
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from snapshot import build_snapshot

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
    return build_snapshot()


@app.get("/api/health")
def health():
    return {"status": "ok"}

"""
Snapshot do scanner — monta o JSON que o dashboard.html consome.

Usado em dois lugares:
  - api.py (GET /api/scan), rodando localmente
  - GitHub Actions (.github/workflows/scan.yml), que roda este arquivo em
    horário de pregão e publica o scan.json no branch `dados`

Rodar manualmente:
  BRAPI_TOKEN=... python snapshot.py scan.json
"""

import json
import sys
from datetime import datetime, timedelta, timezone

from main import scan_market
from paper_portfolio import PaperPortfolio
from correlation_check import check_correlation_limit
from narrator import narrate

BRT = timezone(timedelta(hours=-3))


def build_snapshot(markets=("b3", "intl"), allow_mock: bool = True) -> dict:
    portfolio = PaperPortfolio()
    all_results = []
    for market in markets:
        all_results += scan_market(market, allow_mock=allow_mock)

    for r in all_results:
        if r["signal"] == "HOLD":
            continue
        if not check_correlation_limit(r["symbol"], portfolio.positions):
            r["signal"] = "HOLD"
            r["ai_reasoning"] = "bloqueado por concentração — já há posições correlacionadas abertas"
            continue
        portfolio.apply_signal(r["symbol"], r)

    ranked = sorted(all_results, key=lambda r: r["pct_change"], reverse=True)
    signals = [r for r in all_results if r["signal"] != "HOLD"]

    return {
        "atualizado_em": datetime.now(BRT).isoformat(),
        "dados_simulados": allow_mock,
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


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "scan.json"
    # Painel publicado: só ações B3 com dado real (brapi). Futuros e
    # internacional entram quando Nelogica/IB estiverem conectados.
    snapshot = build_snapshot(markets=("b3",), allow_mock=False)
    if snapshot["total_ativos"] == 0:
        # Não sobrescreve o último scan bom com um vazio (ex: token inválido).
        sys.exit("Nenhum ativo com dado real — confira o BRAPI_TOKEN. scan.json não gerado.")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"{snapshot['total_ativos']} ativos, {len(snapshot['alertas'])} alertas -> {out_path}")

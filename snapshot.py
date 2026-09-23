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
from universe import B3_SECTORS, SECTOR_ORDER

BRT = timezone(timedelta(hours=-3))

# Cotação com último pregão mais antigo que isso é tratada como código que
# parou de negociar (ex: ticker trocado) e fica fora do painel.
MAX_STALE_DAYS = 7

_VOTE_TEXT = {
    ("ma", "BUY"): "médias em alta", ("ma", "SELL"): "médias em baixa",
    ("rsi", "BUY"): "RSI sobrevendido", ("rsi", "SELL"): "RSI sobrecomprado",
    ("bb", "BUY"): "abaixo da banda inferior", ("bb", "SELL"): "acima da banda superior",
}


def _leitura(votes: dict) -> str:
    """Resume em texto médias e Bollinger (o RSI o painel mostra à parte)."""
    parts = [_VOTE_TEXT[(k, v)] for k, v in votes.items() if v != "HOLD" and k != "rsi"]
    return "; ".join(parts) if parts else "médias e bandas sem sinal"


def _asset(r: dict) -> dict:
    votes = r["votes"]
    return {
        "symbol": r["symbol"],
        "setor": B3_SECTORS.get(r["symbol"], "Outros"),
        "price": r["price"],
        "pct_change": r["pct_change"],
        "rsi": r["rsi"],
        "signal": r["signal"],
        "votos_compra": sum(v == "BUY" for v in votes.values()),
        "votos_venda": sum(v == "SELL" for v in votes.values()),
        "leitura": _leitura(votes),
        "ultimo_pregao": r["timestamp"].strftime("%Y-%m-%d"),
        "history": r.get("history"),
    }


def build_snapshot(markets=("b3", "intl"), allow_mock: bool = True, with_history: bool = False) -> dict:
    all_results = []
    for market in markets:
        all_results += scan_market(market, allow_mock=allow_mock, with_history=with_history)

    # Ativo com dados insuficientes pros indicadores volta sem preço/RSI.
    all_results = [r for r in all_results if "price" in r]

    if not allow_mock:
        cutoff = datetime.now() - timedelta(days=MAX_STALE_DAYS)
        fresh = []
        for r in all_results:
            if r["timestamp"].to_pydatetime() < cutoff:
                print(f"[aviso] {r['symbol']}: último pregão {r['timestamp']:%Y-%m-%d} — cotação parada, ignorado")
            else:
                fresh.append(r)
        all_results = fresh

    # Carteira simulada: a trava de concentração limita o que entra na
    # carteira, mas não esconde o sinal técnico do painel.
    portfolio = PaperPortfolio()
    for r in all_results:
        if r["signal"] != "HOLD" and check_correlation_limit(r["symbol"], portfolio.positions):
            portfolio.apply_signal(r["symbol"], r)

    ranked = sorted(all_results, key=lambda r: r["pct_change"], reverse=True)
    signals = [r for r in all_results if r["signal"] != "HOLD"]
    sector_rank = {s: i for i, s in enumerate(SECTOR_ORDER)}

    return {
        "atualizado_em": datetime.now(BRT).isoformat(),
        "dados_simulados": allow_mock,
        "total_ativos": len(all_results),
        "setores": SECTOR_ORDER,
        "top_altas": [
            {"symbol": r["symbol"], "pct_change": r["pct_change"], "price": r["price"]}
            for r in ranked if r["pct_change"] > 0
        ][:5],
        "top_quedas": [
            {"symbol": r["symbol"], "pct_change": r["pct_change"], "price": r["price"]}
            for r in ranked[::-1] if r["pct_change"] < 0
        ][:5],
        "alertas": [
            {"symbol": r["symbol"], "signal": r["signal"], "price": r["price"],
             "mensagem": narrate(r)}
            for r in signals
        ],
        "ativos": sorted(
            (_asset(r) for r in all_results),
            key=lambda a: (sector_rank.get(a["setor"], len(sector_rank)), a["symbol"]),
        ),
        "portfolio": portfolio.summary(),
    }


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "scan.json"
    # Painel publicado: só ações B3 com dado real (brapi). Futuros e
    # internacional entram quando Nelogica/IB estiverem conectados.
    snapshot = build_snapshot(markets=("b3",), allow_mock=False, with_history=True)
    if snapshot["total_ativos"] == 0:
        # Não sobrescreve o último scan bom com um vazio (ex: token inválido).
        sys.exit("Nenhum ativo com dado real — confira o BRAPI_TOKEN. scan.json não gerado.")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{snapshot['total_ativos']} ativos, {len(snapshot['alertas'])} alertas -> {out_path}")

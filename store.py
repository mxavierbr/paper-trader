"""
Persistência do estado da gestão de risco no Supabase.

Sem isso, a "carteira" (posições abertas, caixa, resultado do dia,
drawdown, bloqueios) existe só na memória do processo do backend — e
some a cada novo deploy ou reinício no Render. Este módulo salva e
recarrega esse estado, sem tornar risk.py dependente de nada externo:
a integração fica só aqui.

Lê SUPABASE_URL e SUPABASE_KEY do ambiente. Se não estiverem configuradas
(ex: rodando local sem Supabase), todas as funções viram no-op e o
gestor de risco segue funcionando normalmente, só em memória.
"""

import os
from datetime import date

from risk import GestorDeRisco, Posicao

_SUPABASE_URL = os.environ.get("SUPABASE_URL")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_client = None
_tentou_criar_client = False


def _get_client():
    global _client, _tentou_criar_client
    if _tentou_criar_client:
        return _client
    _tentou_criar_client = True
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return None
    from supabase import create_client
    _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


def carregar_estado(gestor: GestorDeRisco, client=None) -> bool:
    """Hidrata o gestor de risco com o último estado salvo. Retorna True
    se conseguiu falar com o Supabase (mesmo sem dado salvo ainda),
    False se o Supabase não está configurado neste ambiente."""
    client = client if client is not None else _get_client()
    if client is None:
        return False

    estado = client.table("risco_estado").select("*").eq("id", 1).execute()
    if estado.data:
        row = estado.data[0]
        gestor.caixa = float(row["caixa"])
        gestor.pnl_dia = float(row["pnl_dia"])
        gestor.patrimonio_abertura_dia = float(row["patrimonio_abertura_dia"])
        gestor.patrimonio_maximo = float(row["patrimonio_maximo"])
        gestor.bloqueio_diario = bool(row["bloqueio_diario"])
        gestor.bloqueio_drawdown = bool(row["bloqueio_drawdown"])
        gestor._data_referencia = date.fromisoformat(str(row["data_referencia"]))

    posicoes = client.table("posicoes").select("*").execute()
    gestor.posicoes = {}
    for row in posicoes.data:
        pos = Posicao(
            symbol=row["symbol"], setor=row["setor"], qty=int(row["qty"]),
            preco_entrada=float(row["preco_entrada"]), stop=float(row["stop"]),
            alvo=float(row["alvo"]), custo_entrada=float(row["custo_entrada"]),
            maxima_atingida=float(row["maxima_atingida"]),
            trailing_ativo=bool(row["trailing_ativo"]),
        )
        gestor.posicoes[pos.symbol] = pos
        gestor.last_prices[pos.symbol] = pos.preco_entrada

    return True


def salvar_estado(gestor: GestorDeRisco, client=None):
    """Sobrescreve o snapshot do gestor de risco no Supabase. Chamar
    depois de cada ciclo (processar_precos + avaliações de entrada)."""
    client = client if client is not None else _get_client()
    if client is None:
        return

    client.table("risco_estado").upsert({
        "id": 1,
        "caixa": gestor.caixa,
        "pnl_dia": gestor.pnl_dia,
        "patrimonio_abertura_dia": gestor.patrimonio_abertura_dia,
        "patrimonio_maximo": gestor.patrimonio_maximo,
        "bloqueio_diario": gestor.bloqueio_diario,
        "bloqueio_drawdown": gestor.bloqueio_drawdown,
        "data_referencia": gestor._data_referencia.isoformat(),
    }).execute()

    symbols_abertos = list(gestor.posicoes.keys())
    for pos in gestor.posicoes.values():
        client.table("posicoes").upsert({
            "symbol": pos.symbol, "setor": pos.setor, "qty": pos.qty,
            "preco_entrada": pos.preco_entrada, "stop": pos.stop, "alvo": pos.alvo,
            "custo_entrada": pos.custo_entrada, "maxima_atingida": pos.maxima_atingida,
            "trailing_ativo": pos.trailing_ativo,
        }).execute()

    query = client.table("posicoes").delete()
    query = query.not_.in_("symbol", symbols_abertos) if symbols_abertos else query.neq("symbol", "")
    query.execute()


def registrar_trades(trade_log_novos: list, client=None):
    """Insere no histórico (tabela trades, append-only) os trades novos
    de um ciclo — symbol/action/qty/price/realized_pnl de cada entrada
    do trade_log do PaperPortfolio."""
    client = client if client is not None else _get_client()
    if client is None or not trade_log_novos:
        return

    linhas = [
        {
            "symbol": t["symbol"], "action": t["action"], "qty": t.get("qty", 0),
            "preco": t.get("price", 0.0), "realized_pnl": t.get("realized_pnl", 0.0),
        }
        for t in trade_log_novos
    ]
    client.table("trades").insert(linhas).execute()

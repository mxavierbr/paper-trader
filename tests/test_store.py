"""Testes de store.py com um cliente Supabase falso (sem rede)."""

import store
from risk import RiskConfig, GestorDeRisco


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, recorder, table_name, data):
        self.recorder = recorder
        self.table_name = table_name
        self.data = data

    def select(self, *a):
        self.recorder.append((self.table_name, "select", a))
        return self

    def eq(self, *a):
        self.recorder.append((self.table_name, "eq", a))
        return self

    def upsert(self, row):
        self.recorder.append((self.table_name, "upsert", row))
        return self

    def insert(self, rows):
        self.recorder.append((self.table_name, "insert", rows))
        return self

    def delete(self):
        self.recorder.append((self.table_name, "delete", None))
        return self

    @property
    def not_(self):
        return self

    def in_(self, col, values):
        self.recorder.append((self.table_name, "not_in", (col, values)))
        return self

    def neq(self, col, val):
        self.recorder.append((self.table_name, "neq", (col, val)))
        return self

    def execute(self):
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self, dados_iniciais=None):
        self.recorder = []
        self.dados = dados_iniciais or {}

    def table(self, name):
        return FakeQuery(self.recorder, name, self.dados.get(name, []))


def _chamadas(client, table_name, op):
    return [c for c in client.recorder if c[0] == table_name and c[1] == op]


def test_carregar_estado_sem_client_retorna_false():
    gestor = GestorDeRisco(RiskConfig())
    assert store.carregar_estado(gestor, client=None) is False


def test_carregar_estado_hidrata_gestor():
    dados = {
        "risco_estado": [{
            "id": 1, "caixa": 5000.0, "pnl_dia": -100.0,
            "patrimonio_abertura_dia": 10000.0, "patrimonio_maximo": 12000.0,
            "bloqueio_diario": True, "bloqueio_drawdown": False,
            "data_referencia": "2024-01-01",
        }],
        "posicoes": [{
            "symbol": "PETR4", "setor": "petroleo", "qty": 100,
            "preco_entrada": 30.0, "stop": 28.0, "alvo": 34.0,
            "custo_entrada": 1.5, "maxima_atingida": 31.0, "trailing_ativo": True,
        }],
    }
    client = FakeClient(dados)
    gestor = GestorDeRisco(RiskConfig(), patrimonio_inicial=100.0)

    ok = store.carregar_estado(gestor, client=client)

    assert ok is True
    assert gestor.caixa == 5000.0
    assert gestor.pnl_dia == -100.0
    assert gestor.bloqueio_diario is True
    assert gestor.bloqueio_drawdown is False
    assert "PETR4" in gestor.posicoes
    assert gestor.posicoes["PETR4"].qty == 100
    assert gestor.posicoes["PETR4"].trailing_ativo is True
    assert gestor.last_prices["PETR4"] == 30.0


def test_salvar_estado_grava_snapshot_e_posicoes():
    client = FakeClient()
    gestor = GestorDeRisco(RiskConfig())
    gestor.abrir_posicao("PETR4", "petroleo", 100, 30.0, stop=28.0, alvo=34.0)

    store.salvar_estado(gestor, client=client)

    upserts_estado = _chamadas(client, "risco_estado", "upsert")
    assert len(upserts_estado) == 1
    assert upserts_estado[0][2]["caixa"] == gestor.caixa

    upserts_posicao = _chamadas(client, "posicoes", "upsert")
    assert len(upserts_posicao) == 1
    assert upserts_posicao[0][2]["symbol"] == "PETR4"

    assert len(_chamadas(client, "posicoes", "delete")) == 1


def test_registrar_trades_insere_linhas_convertidas():
    client = FakeClient()
    trade_log = [
        {"symbol": "PETR4", "action": "BUY", "price": 30.0, "qty": 100,
         "realized_pnl": 0.0, "timestamp": "2024-01-01"},
    ]
    store.registrar_trades(trade_log, client=client)

    inserts = _chamadas(client, "trades", "insert")
    assert len(inserts) == 1
    assert inserts[0][2][0]["symbol"] == "PETR4"
    assert inserts[0][2][0]["preco"] == 30.0


def test_registrar_trades_vazio_nao_chama_client():
    client = FakeClient()
    store.registrar_trades([], client=client)
    assert client.recorder == []

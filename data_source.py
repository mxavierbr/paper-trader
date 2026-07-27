"""
Camada de dados — interface plugável.

Hoje: gera série sintética (random walk com drift) para permitir testar
o motor de indicadores/sinal/paper trading sem depender de credenciais
de corretora.

Para produção: trocar MockDataSource por um adapter real
(ex: NelogicaDataSource usando a DLL/API do Profit para WIN/WDO,
ou TwelveDataSource para futuros CBOT), mantendo a mesma interface
get_ohlcv(symbol, periods) -> DataFrame.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class DataSource:
    def get_ohlcv(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        raise NotImplementedError

    def list_universe(self, market: str) -> list:
        """Retorna a lista de todos os símbolos negociáveis de um mercado
        ('b3' ou 'intl'). Implementação real: brapi.dev tem endpoint de
        listagem de todos os ativos da B3; IB tem contract search
        (reqMatchingSymbols) para o universo internacional."""
        raise NotImplementedError


class MockDataSource(DataSource):
    """Gera candles sintéticos plausíveis para um símbolo, com seed
    determinística por símbolo (mesma sequência sempre, para reprodutibilidade
    em testes)."""

    BASE_PRICES = {
        "WINFUT": 132000,   # Mini Índice (pontos)
        "WDOFUT": 5450,     # Mini Dólar (R$ x 1000, valor ilustrativo de teste)
        "ZCFUT": 445,       # Milho CBOT (cents/bushel, valor ilustrativo de teste)
        "ESFUT": 5600,      # E-mini S&P 500 (pontos, valor ilustrativo de teste)
        "AAPL": 230, "MSFT": 460, "GOOGL": 175, "AMZN": 210, "TSLA": 250,
        "NVDA": 140, "META": 590, "JPM": 245, "KO": 68, "XOM": 115,
        "EMBR3": 55, "PETR4": 38, "AZUL4": 8, "JBSS3": 34,
        "VALE3": 62, "ITUB4": 34, "BBDC4": 15, "ABEV3": 12, "WEGE3": 42,
        "GGBR4": 21, "SUZB3": 55, "RENT3": 58, "RAIL3": 20, "BRFS3": 24, "BBAS3": 26,
    }

    # Classifica o ativo — futuros têm ajuste diário e margem; ações não.
    # Usado depois pelo adapter real (IB/corretora B3) para montar o tipo de contrato certo.
    ASSET_TYPE = {
        "WINFUT": "future", "WDOFUT": "future", "ZCFUT": "future", "ESFUT": "future",
    }
    _B3_TICKERS = {"EMBR3", "PETR4", "AZUL4", "JBSS3", "VALE3", "ITUB4", "BBDC4",
                   "ABEV3", "WEGE3", "GGBR4", "SUZB3", "RENT3", "RAIL3", "BRFS3", "BBAS3"}

    def __init__(self):
        for s in self.BASE_PRICES:
            if s not in self.ASSET_TYPE:
                self.ASSET_TYPE[s] = "stock"

    def list_universe(self, market: str) -> list:
        """Simula o universo completo. Em produção, trocar por chamada real:
        brapi.dev /api/quote/list (B3) ou IB reqMatchingSymbols (internacional)."""
        if market == "b3":
            futures = {"WINFUT", "WDOFUT"}
            return sorted(futures | self._B3_TICKERS)
        return sorted(set(self.BASE_PRICES) - self._B3_TICKERS - {"WINFUT", "WDOFUT"})

    def get_ohlcv(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        base = self.BASE_PRICES.get(symbol, 100)
        rng = np.random.default_rng(abs(hash(symbol)) % (2**32))
        returns = rng.normal(loc=0.0002, scale=0.006, size=periods)
        close = base * np.cumprod(1 + returns)

        high = close * (1 + np.abs(rng.normal(0, 0.003, periods)))
        low = close * (1 - np.abs(rng.normal(0, 0.003, periods)))
        open_ = np.roll(close, 1)
        open_[0] = base
        volume = rng.integers(1000, 50000, periods)

        now = datetime.now()
        idx = [now - timedelta(minutes=5 * (periods - i)) for i in range(periods)]

        df = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=pd.DatetimeIndex(idx, name="timestamp"),
        )
        return df


class BrapiDataSource(DataSource):
    """
    Adapter real para ações B3 via brapi.dev.

    Sandbox sem token: PETR4, VALE3, MGLU3, ITUB4. Para os demais símbolos
    (EMBR3, AZUL4, JBSS3, BBAS3 etc.) e para uso em produção, é preciso
    criar um token gratuito em https://brapi.dev/dashboard (15 mil
    requisições/mês no plano free).

    Cobre só AÇÕES — futuros (WINFUT, WDOFUT) continuam precisando da
    Nelogica; a brapi tem endpoint de futuros mas não cobre WIN/WDO com
    a granularidade intraday necessária para o motor de sinal.
    """

    BASE_URL = "https://brapi.dev/api/v2/stocks"

    def __init__(self, token: str = None):
        self.token = token

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get_ohlcv(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        import urllib.request
        import urllib.parse
        import urllib.error
        import json as _json

        # range aproximado pra cobrir 'periods' dias úteis com folga
        range_days = "3mo" if periods <= 90 else "1y"
        url = f"{self.BASE_URL}/historical?" + urllib.parse.urlencode(
            {"symbols": symbol, "range": range_days, "interval": "1d"}
        )
        req = urllib.request.Request(url, headers=self._headers())

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"Falha ao consultar brapi.dev para {symbol}: {e}")

        try:
            candles = data["results"][0]["data"]["historicalDataPrice"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Resposta inesperada da brapi.dev para {symbol}: {data}")

        rows = candles[-periods:]
        df = pd.DataFrame({
            "open": [r["open"] for r in rows],
            "high": [r["high"] for r in rows],
            "low": [r["low"] for r in rows],
            "close": [r["close"] for r in rows],
            "volume": [r.get("volume", 0) for r in rows],
        }, index=pd.DatetimeIndex(
            [datetime.fromtimestamp(r["date"]) for r in rows], name="timestamp"
        ))
        return df


class NelogicaDataSource(DataSource):
    """
    Adapter para B3 — futuros (WINFUT, WDOFUT) e ações (EMBR3, PETR4, AZUL4,
    JBSS3 etc.) via DLL/API da Nelogica (Profit).

    Nota: para ações à vista, uma alternativa mais simples que a DLL da
    Nelogica é usar brapi.dev só para os dados de cotação (mais fácil de
    integrar) e a API/homebroker da própria corretora só para enviar a
    ordem de execução. Vale essa divisão se a Nelogica não for necessária
    para os futuros no mesmo projeto.

    STUB — não funcional ainda. Requer:
      - Conta em corretora com acesso à API/DLL da Nelogica liberado
        (confirmar com a corretora; nem todo plano inclui)
      - Credenciais fornecidas pela Nelogica (login + chave de ativação da API)
      - SDK: a Nelogica distribui uma DLL (Windows) com bindings; em Python
        normalmente se integra via ctypes ou um wrapper de terceiros

    Quando as credenciais estiverem disponíveis, implementar aqui:
      1. Autenticar na API
      2. Assinar (subscribe) o book/candles do símbolo
      3. Converter o retorno para o mesmo formato de DataFrame do MockDataSource
         (colunas: open, high, low, close, volume; índice: timestamp)
    """

    def __init__(self, login: str = None, api_key: str = None):
        self.login = login
        self.api_key = api_key

    def get_ohlcv(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        raise NotImplementedError(
            "NelogicaDataSource ainda não implementado — configure credenciais "
            "da API Nelogica/Profit e implemente a chamada real aqui."
        )


class InteractiveBrokersDataSource(DataSource):
    """
    Adapter para CBOT/CME (futuros: ZCFUT, ESFUT) e ações de multinacionais
    (AAPL, MSFT etc.) via Interactive Brokers.

    Nota sobre single-stock futures: existem na IB para algumas ações, mas
    liquidez costuma ser baixa — vale checar disponibilidade e volume antes
    de incluir no motor de sinal. Ações à vista (STK) têm liquidez muito
    maior e cobrem o mesmo objetivo de exposição à multinacional.

    STUB — não funcional ainda. Requer:
      - Conta na Interactive Brokers com acesso a futuros CBOT
      - TWS ou IB Gateway rodando (a API do IB não é REST simples — precisa
        de um desses dois rodando localmente ou em servidor)
      - Biblioteca oficial: `ibapi` (pip install ibapi) ou o wrapper mais
        usado na comunidade, `ib_insync`

    Quando a conta estiver aberta, implementar aqui:
      1. Conectar ao TWS/Gateway (host, porta, client_id)
      2. Requisitar histórico de candles (reqHistoricalData) para o contrato
      3. Converter o retorno para o mesmo formato de DataFrame do MockDataSource
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id

    def get_ohlcv(self, symbol: str, periods: int = 200) -> pd.DataFrame:
        raise NotImplementedError(
            "InteractiveBrokersDataSource ainda não implementado — abra a conta, "
            "rode o TWS/IB Gateway e implemente a chamada real aqui."
        )


def get_data_source(symbol: str) -> DataSource:
    """
    Roteador: decide qual adapter usar conforme o símbolo.

    Ações B3 -> BrapiDataSource (real, funciona hoje com token gratuito)
    Futuros B3 (WINFUT, WDOFUT) -> Nelogica (ainda stub — depende de conta)
    Internacional (futuros + ações) -> Interactive Brokers (ainda stub)
    """
    b3_futures = {"WINFUT", "WDOFUT"}
    b3_stocks = set(MockDataSource().list_universe("b3")) - b3_futures

    if symbol in b3_futures:
        # return NelogicaDataSource(login=..., api_key=...)
        return MockDataSource()
    if symbol in b3_stocks:
        import os
        return BrapiDataSource(token=os.environ.get("BRAPI_TOKEN"))
    # return InteractiveBrokersDataSource()
    return MockDataSource()


def get_universe(market: str) -> list:
    """Lista todos os símbolos negociáveis do mercado ('b3' ou 'intl')."""
    return MockDataSource().list_universe(market)


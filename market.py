"""
Contexto de mercado para o painel: Ibovespa, dólar PTAX e status do pregão.

- Ibovespa: brapi.dev (^BVSP), mesmo token e mesmo limite de 3 meses.
- Dólar: PTAX venda oficial do Banco Central (SGS, série 1), API pública
  sem token: https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados
- Pregão: aberto em dia útil entre 10h e 18h (Brasília) *e* se já houver
  candle do dia — assim feriados aparecem como fechado sem manter
  calendário de feriados.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from analytics import pct
from data_source import BrapiDataSource

BRT = timezone(timedelta(hours=-3))
# O endpoint "ultimos/N" aceita no máximo N=20; por intervalo de datas não há esse limite.
PTAX_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial={ini}&dataFinal={fim}"


def fetch_ibovespa() -> dict | None:
    try:
        df = BrapiDataSource(token=os.environ.get("BRAPI_TOKEN")).get_ohlcv("^BVSP")
    except RuntimeError as e:
        print(f"[aviso] Ibovespa indisponível: {e}")
        return None
    close = df["close"]
    last = float(close.iloc[-1])
    return {
        "valor": round(last),
        "var_dia": pct(float(close.iloc[-2]), last),
        "var_5d": pct(float(close.iloc[-6]), last) if len(close) > 5 else None,
        "var_21d": pct(float(close.iloc[-22]), last) if len(close) > 21 else None,
        "data": df.index[-1].strftime("%Y-%m-%d"),
        "serie": [round(float(v)) for v in close],
    }


def fetch_ptax() -> dict | None:
    try:
        today = datetime.now(BRT)
        url = PTAX_URL.format(ini=(today - timedelta(days=60)).strftime("%d/%m/%Y"),
                              fim=today.strftime("%d/%m/%Y"))
        with urllib.request.urlopen(url, timeout=15) as resp:
            rows = json.loads(resp.read())
    except (urllib.error.URLError, ValueError) as e:
        print(f"[aviso] PTAX indisponível: {e}")
        return None
    vals = [float(r["valor"]) for r in rows]
    if len(vals) < 2:
        return None
    d, m, y = rows[-1]["data"].split("/")
    return {
        "valor": vals[-1],
        "var_dia": pct(vals[-2], vals[-1]),
        "var_21d": pct(vals[-22], vals[-1]) if len(vals) > 21 else None,
        "data": f"{y}-{m}-{d}",
        "serie": vals,
    }


def market_status(last_trading_date: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(BRT)
    today = now.strftime("%Y-%m-%d")
    open_now = (now.weekday() < 5 and 10 <= now.hour < 18 and last_trading_date == today)
    return {
        "aberto": open_now,
        "cotacao_de": last_trading_date,
        "atraso_min": 30,  # plano gratuito da brapi: cotação com ~30 min de atraso
    }

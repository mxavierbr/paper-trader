# Pendências — Paper Trader (integrações reais a fazer)

## Dados de mercado
- [ ] Conta em corretora com API/DLL da Nelogica liberada (B3: WINFUT, WDOFUT, ações)
- [ ] Conta na Interactive Brokers + TWS/IB Gateway rodando (CBOT/CME: ZCFUT, ESFUT, AAPL, MSFT)
- [ ] Trocar `MockDataSource` pelos adapters reais em `data_source.py`
- [ ] Trocar `list_universe()` mock pela listagem real (brapi.dev para B3; IB reqMatchingSymbols para internacional)

## Notícias e fundamentos
- [ ] Integrar Fatos Relevantes da CVM/B3 em `news_context.py` (fonte oficial, sai antes da notícia)
- [ ] Integrar brapi.dev (balanços B3) e Alpha Vantage (fundamentals internacional) em `fundamentals.py`

## IA
- [ ] Configurar `ANTHROPIC_API_KEY` no backend (nunca no app mobile) para `ai_layer.py` funcionar de verdade

## Calendário de eventos
- [ ] Integrar calendário público do Bacen (Copom) e do Fed em `event_calendar.py`
- [ ] Integrar datas de divulgação de balanço por empresa (RI/CVM)

## Validação
- [ ] Rodar `backtest.py` contra histórico real (2+ anos) assim que houver dado real — com mock não tem valor preditivo
- [ ] Rodar em paper trading real (dado ao vivo, sem executar ordem) por algumas semanas antes de cogitar execução real

## Painel mobile
- [x] Painel web estático (`dashboard.html`) — funciona, mas dado é foto fixa, não ao vivo
- [ ] Transformar `main.py` numa API (ex: FastAPI) rodando num servidor contínuo
- [ ] Trocar o objeto `DATA` fixo no `dashboard.html` por `fetch()` na API real

## Execução real (só depois de tudo acima validado)
- [ ] Implementar envio de ordem real nos adapters (hoje só leem dado, não operam)
- [ ] Revisar `RiskConfig` (capital, % de risco por trade, exposição máxima) para o capital real

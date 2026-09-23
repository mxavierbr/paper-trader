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
- [ ] **Antes de ligar a IA:** `news_context.py` e `fundamentals.py` ainda devolvem manchetes/fundamentos fictícios (mock). Com a chave configurada, a IA julgaria o sinal com base nesse texto inventado — trocar por fonte real primeiro

## Calendário de eventos
- [ ] Integrar calendário público do Bacen (Copom) e do Fed em `event_calendar.py`
- [ ] Integrar datas de divulgação de balanço por empresa (RI/CVM)

## Validação
- [ ] Rodar `backtest.py` contra histórico real (2+ anos) assim que houver dado real — com mock não tem valor preditivo
- [ ] Rodar em paper trading real (dado ao vivo, sem executar ordem) por algumas semanas antes de cogitar execução real

## Painel mobile (Opção 2: Netlify + GitHub Actions — ver docs/decisoes.md)
- [x] Painel web (`dashboard.html`) lendo dados via `fetch()`
- [x] `snapshot.py` gera o `scan.json` (só ações B3 com dado real, sem mock)
- [x] Agendamento `.github/workflows/scan.yml` (a cada 30 min no pregão, publica no branch `dados`)
- [x] `netlify.toml` publica o painel sem gastar deploy a cada atualização de dados
- [ ] Criar token gratuito em brapi.dev e cadastrar como secret `BRAPI_TOKEN` no GitHub
- [x] Token brapi cadastrado (secret `BRAPI_TOKEN`), workflow rodando na `main`, painel no ar em https://mx-paper-trader.netlify.app
- [x] Painel v2: todas as ações com RSI/tendência/sinal, filtro por setor (Agro, Proteína, Papel e celulose, Logística, Outros) e gráfico de 3 meses por ação
- [ ] (Opcional) Cadastrar secret `ANTHROPIC_API_KEY` para ligar a camada de IA (ver pendência da IA acima)
- [ ] Carteira simulada persistente entre varreduras (hoje recomeça a cada execução; oculta no painel)
- [x] Painel v3: faixa de mercado (Ibovespa, dólar PTAX do BCB, status do pregão), tabela única ordenável com mini-gráfico, detalhe com variação 1 semana/1 mês/3 meses e acerto histórico dos sinais
- [ ] (Opcional) Avisos no celular (Telegram) quando surgir sinal novo
- [x] Atraso mínimo no plano gratuito: varredura a cada 20 min (10:27–17:47 + 18:37), painel lê via API do GitHub (cache 60 s, volta para o link raw se a API recusar) e mostra "Atualizado há X min"
- [ ] Menos atraso que ~30 min exige fonte paga: brapi Startup (~15 min) / Pro (~5 min), ou tempo real via API da corretora (Nelogica/Profit)
- [ ] Acerto histórico com amostra maior: hoje usa 3 meses (limite do plano gratuito da brapi); com 2+ anos o percentual passa a ter peso estatístico

## Execução real (só depois de tudo acima validado)
- [ ] Implementar envio de ordem real nos adapters (hoje só leem dado, não operam)
- [ ] Revisar `RiskConfig` (capital, % de risco por trade, exposição máxima) para o capital real

# Paper Trader — instruções para o Claude

## Salvar automaticamente ao encerrar

Sempre que o usuário se despedir ou sinalizar uma pausa na conversa — frases como
"até amanhã", "amanhã continuamos", "boa noite", "até mais tarde", "tchau", ou
equivalentes — faça, sem precisar perguntar antes:

1. Verifique se há alterações não commitadas neste repositório (`git status`).
2. Se houver, faça `git add` dos arquivos relevantes e `git commit` com uma
   mensagem descritiva do que foi feito na sessão.
3. Dê `git push` para o branch atual.
4. Confirme para o usuário, em uma frase curta, que ficou salvo.

Essa autorização já foi dada previamente pelo usuário — não é necessário pedir
confirmação a cada vez, só ao identificar uma despedida/pausa.

## Continuidade entre sessões

Cada sessão do Claude Code começa sem memória de conversas anteriores. O que
persiste é só o que está commitado neste repositório. Para retomar de onde uma
sessão anterior parou, leia antes de assumir que algo não foi feito ainda:

- `PENDENCIAS.md` — lista de integrações reais ainda pendentes (dados de mercado
  via Nelogica/Interactive Brokers, notícias CVM/B3, IA, calendário de eventos,
  validação por backtest/paper trading real, painel mobile, execução real).
- `docs/decisoes.md` — decisões de arquitetura/produto já tomadas.

## Sobre o projeto

Sistema de paper trading (simulação de operações, sem execução real ainda) com
camada de IA (`ai_layer.py`), engine de sinais (`signal_engine.py`), gestão de
risco (`risk_manager.py`) e painel web estático (`dashboard.html`). Hoje roda
sobre dados mockados (`MockDataSource`) — a integração com dados reais é a
pendência central, listada em `PENDENCIAS.md`.

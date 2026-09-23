# Registro de Decisões

Histórico das decisões técnicas e de produto tomadas neste repositório. Cada entrada deve ser objetiva: contexto, decisão, alternativas descartadas e motivo.

## Formato de cada entrada

## [AAAA-MM-DD] Título curto da decisão

**Contexto:** por que essa decisão precisou ser tomada.

**Decisão:** o que foi decidido.

**Alternativas consideradas:** o que mais foi avaliado e por que foi descartado.

**Impacto:** o que muda no sistema/processo a partir daqui.

---

## [2026-09-23] Painel pessoal: Netlify + GitHub Actions, sem servidor contínuo

**Contexto:** o painel é de uso pessoal (acompanhar ações e sinais de compra/venda pelo celular), não vai para lojas de apps. A API FastAPI precisaria de um servidor ligado 24h, e o Netlify não roda Python nem processos contínuos. No plano gratuito do Netlify com créditos, cada deploy de produção consome 15 dos 300 créditos mensais (cerca de 20 deploys por mês).

**Decisão:** um agendamento no GitHub Actions roda `snapshot.py` a cada 30 min durante o pregão da B3 e publica o `scan.json` no branch `dados` (um único commit, sobrescrito a cada execução). O Netlify hospeda só o `dashboard.html`, que lê o `scan.json` direto de `raw.githubusercontent.com`. O Netlify só faz deploy quando o painel muda. O painel publicado mostra apenas ações B3 com dado real (brapi.dev); ativos sem fonte real são descartados, não simulados.

**Alternativas consideradas:**
- Servidor contínuo (VPS/Render) rodando a API: custo mensal e manutenção desnecessários para uso pessoal.
- Publicar o `scan.json` via deploy do Netlify a cada execução: estouraria os créditos do plano gratuito.
- Rodar só no PC local: não permite consultar pelo celular fora de casa.

**Impacto:** custo zero (repositório público: Actions gratuito; Netlify só com deploys eventuais). Os dados ficam públicos no GitHub (só cotações e sinais, nada sensível). Futuros B3 (WIN/WDO via Nelogica) e internacionais (IB) ficam fora do painel publicado até existir fonte real, pois dependem de conexão local. A execução agendada do GitHub pode atrasar alguns minutos.

---

## [2026-09-23] Nome e identidade do painel: Trendo

**Contexto:** o painel publicado precisava de um nome comercial, neutro de setor (a carteira tem agro, bancos, mineração, indústria), distinto do produto já existente "RadarJox".

**Decisão:** nome **Trendo** (derivado de "trend", tendência), subtítulo "Leia a tendência.". Logo: um "t" cuja barra vira linha de tendência de alta, com ponto dourado no destino. Arquivos em `assets/` (SVG, PNGs 180/192/512 e manifest para instalar no celular).

**Alternativas consideradas:** Talhão, AgroSinal, Colheita, Silo (ligados só ao agro); Faro, Tino, Vértice, Pulso; Vela, Zênite, Kairós, Ímpeto, Norte. Descartados por preferência do dono do projeto. Evitados nomes de empresas conhecidas do mercado (Safra, Rumo, Prumo).

**Impacto:** nome, ícone e título aparecem no painel, na aba do navegador e no ícone da tela inicial. Antes de uso comercial, pesquisar o nome no INPI e disponibilidade de domínio (não verificado).

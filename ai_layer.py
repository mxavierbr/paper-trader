"""
Camada de IA — segundo filtro sobre o sinal técnico.

Recebe o sinal técnico (BUY/SELL/HOLD) + manchetes recentes da empresa e
pede para o modelo confirmar, reforçar ou vetar o sinal, considerando
contexto que o indicador técnico sozinho não vê (ex: negociação de
contrato internacional ainda não totalmente precificada).

Chama a API da Anthropic diretamente (api.anthropic.com). Requer a
variável de ambiente ANTHROPIC_API_KEY configurada no ambiente onde
o pipeline rodar de verdade (servidor/backend do app — não faz sentido
colocar a chave no app mobile). Se a chave não estiver configurada,
cai de volta no sinal técnico puro (fail-safe, não quebra o pipeline).
"""

import os
import json
import urllib.request
import urllib.error

MODEL = "claude-sonnet-4-6"


def _call_claude(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    body = json.dumps({
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return "".join(b["text"] for b in data["content"] if b["type"] == "text")
    except urllib.error.URLError:
        return None


def refine_signal(technical_signal: dict, headlines: list, fundamentals: dict = None) -> dict:
    """Combina o sinal técnico com contexto de notícias e fundamentos.
    Retorna o mesmo dict do sinal técnico, com 'signal' possivelmente
    ajustado e um campo 'ai_reasoning' explicando o porquê (ou None se a
    IA não rodou)."""

    fundamentals = fundamentals or {}
    if not headlines and not fundamentals:
        return {**technical_signal, "ai_reasoning": None}

    fundamentals_txt = (
        "\n".join(f"- {k}: {v}" for k, v in fundamentals.items())
        if fundamentals else "sem dados fundamentalistas disponíveis"
    )

    prompt = (
        f"Ativo: {technical_signal['symbol']}\n"
        f"Sinal técnico atual: {technical_signal['signal']} "
        f"(preço {technical_signal['price']}, RSI {technical_signal['rsi']})\n"
        f"Manchetes recentes:\n" + "\n".join(f"- {h}" for h in headlines) + "\n\n"
        f"Dados fundamentalistas (balanço/resultado):\n{fundamentals_txt}\n\n"
        "Ao decidir, considere também:\n"
        "1. O setor do ativo — setores com regulação/auditoria mais rígida "
        "(ex: bancário, sob supervisão do Bacen) tendem a ter balanços mais "
        "confiáveis; setores menos regulados pedem mais cautela.\n"
        "2. Balanço reportado não é garantia de realidade — houve casos "
        "graves de balanço não refletir a situação real da empresa "
        "(ex: Lojas Americanas, 2023), causando queda drástica quando a "
        "fraude veio à tona. Antes de recomendar compra com base só no "
        "balanço, cheque se há 'sinais_de_risco_contabil' listados nos "
        "dados fundamentalistas e trate qualquer sinal como motivo de cautela.\n\n"
        "Considerando notícias, fundamentos, setor e risco de confiabilidade "
        "do balanço, o sinal técnico deve ser mantido, reforçado ou vetado? "
        "Responda em JSON: "
        '{"signal": "BUY|SELL|HOLD", "reasoning": "explicação curta em português"}'
    )

    raw = _call_claude(prompt)
    if raw is None:
        return {**technical_signal, "ai_reasoning": "IA não configurada (ANTHROPIC_API_KEY ausente) — usando sinal técnico puro"}

    try:
        parsed = json.loads(raw.strip().strip("`").removeprefix("json").strip())
        return {**technical_signal, "signal": parsed["signal"], "ai_reasoning": parsed["reasoning"]}
    except (json.JSONDecodeError, KeyError):
        return {**technical_signal, "ai_reasoning": f"IA respondeu fora do formato esperado: {raw[:200]}"}

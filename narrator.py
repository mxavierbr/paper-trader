"""
Narrador — traduz o sinal técnico em recomendação em linguagem natural,
dirigida ao usuário. Pensado para virar notificação push no app mobile.
"""

USER_NAME = "Maurício"


def narrate(signal: dict) -> str:
    symbol = signal["symbol"]
    action = signal["signal"]
    price = signal["price"]
    rsi = signal["rsi"]

    if signal.get("risco_motivo"):
        msg = (f"{USER_NAME}, o sinal técnico indicava {action} em {symbol} "
               f"(preço {price}), mas a gestão de risco recusou a entrada: "
               f"{signal['risco_motivo']}.")
        if signal.get("ai_reasoning"):
            msg += f" [IA: {signal['ai_reasoning']}]"
        return msg

    if action == "BUY":
        if rsi < 30:
            razao = "o preço caiu bastante e está sobrevendido"
        else:
            razao = "os indicadores viraram pra alta"

        if signal.get("reforco_posicao"):
            msg = (f"{USER_NAME}, você já tem {symbol} na carteira e o sinal é de compra de novo "
                   f"— {razao}. Pode reforçar a posição. Preço atual: {price}.")
        else:
            msg = (f"{USER_NAME}, pode comprar {symbol} — {razao}. "
                   f"Preço atual: {price}. Tendência de subir.")

    elif action == "SELL":
        if rsi > 70:
            razao = "o preço subiu demais e está sobrecomprado"
        else:
            razao = "os indicadores viraram pra queda"
        msg = (f"{USER_NAME}, para de comprar {symbol} — {razao}. "
               f"Preço atual: {price}. Pode começar a cair a qualquer momento.")

    elif signal.get("motivo_veto_tecnico"):
        msg = (f"{USER_NAME}, {symbol} ainda não confirma entrada nem saída — "
               f"{signal['motivo_veto_tecnico']}. Preço atual: {price}. Só observar.")

    else:
        msg = f"{USER_NAME}, {symbol} sem sinal claro agora ({price}, RSI {rsi}). Só observar."

    if signal.get("ai_reasoning"):
        msg += f" [IA: {signal['ai_reasoning']}]"

    return msg


_RAZOES_SAIDA = {
    "STOP": "bateu o stop de proteção",
    "TRAILING": "bateu o trailing stop — protegendo o lucro que já tinha",
    "ALVO": "atingiu o alvo",
    "SINAL_TECNICO": "o sinal técnico virou",
}


def narrate_saida(evento: dict) -> str:
    """Mensagem pra quando uma posição da carteira é fechada — seja por
    stop, trailing, alvo ou reversão do sinal técnico."""
    symbol = evento["symbol"]
    motivo = evento["motivo"]
    preco = evento["preco_saida"]
    pnl = evento["pnl"]
    razao = _RAZOES_SAIDA.get(motivo, motivo)
    resultado = "lucro" if pnl >= 0 else "prejuízo"

    return (f"{USER_NAME}, é hora de vender {symbol} — {razao}. "
            f"Preço de saída: {preco}. Resultado: {resultado} de {abs(pnl):.2f}.")

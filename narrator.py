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

    if action == "BUY":
        if rsi < 30:
            razao = "o preço caiu bastante e está sobrevendido"
        else:
            razao = "os indicadores viraram pra alta"
        msg = (f"{USER_NAME}, pode comprar mais {symbol} — {razao}. "
               f"Preço atual: {price}. Tendência de subir.")

    elif action == "SELL":
        if rsi > 70:
            razao = "o preço subiu demais e está sobrecomprado"
        else:
            razao = "os indicadores viraram pra queda"
        msg = (f"{USER_NAME}, para de comprar {symbol} — {razao}. "
               f"Preço atual: {price}. Pode começar a cair a qualquer momento.")

    else:
        msg = f"{USER_NAME}, {symbol} sem sinal claro agora ({price}, RSI {rsi}). Só observar."

    if signal.get("ai_reasoning"):
        msg += f" [IA: {signal['ai_reasoning']}]"

    return msg

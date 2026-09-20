"""Portfólio simulado (paper trading). Não envia nenhuma ordem real.

O dimensionamento de posição, stop/alvo e os tetos de exposição são
decididos pela camada de gestão de risco (risk.py) — aqui só registra
o resultado da decisão (trade_log) e o caixa/posições para o dashboard.
"""

from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    qty: int = 0
    avg_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class PaperPortfolio:
    cash: float = 0.0
    positions: dict = field(default_factory=dict)
    trade_log: list = field(default_factory=list)

    def _exposure_value(self) -> float:
        return sum(p.qty * p.avg_price for p in self.positions.values() if p.qty > 0)

    def apply_signal(self, symbol: str, signal: dict, avaliacao_risco: dict = None):
        """Registra o trade no log. Para BUY, exige uma avaliação aprovada
        pelo GestorDeRisco (qty, stop, alvo já dimensionados)."""
        action = signal["signal"]
        price = signal.get("price")
        if action == "HOLD" or price is None:
            return

        pos = self.positions.get(symbol, Position(symbol))

        if action == "BUY":
            if not avaliacao_risco or not avaliacao_risco.get("aprovado"):
                return  # sem aprovação da gestão de risco, não vira ordem

            qty = avaliacao_risco["qty"]
            pos.avg_price = (
                (pos.avg_price * pos.qty + price * qty) / (pos.qty + qty)
                if pos.qty > 0 else price
            )
            pos.qty += qty
            pos.stop_loss = avaliacao_risco["stop"]
            pos.take_profit = avaliacao_risco["alvo"]

            self.positions[symbol] = pos
            self.trade_log.append(
                {"symbol": symbol, "action": "BUY", "price": price, "qty": qty,
                 "stop_loss": pos.stop_loss, "take_profit": pos.take_profit,
                 "realized_pnl": 0.0, "timestamp": signal["timestamp"]}
            )

        elif action == "SELL" and pos.qty > 0:
            realized = (price - pos.avg_price) * pos.qty
            self.cash += realized
            self.trade_log.append(
                {"symbol": symbol, "action": "SELL", "price": price, "qty": pos.qty,
                 "realized_pnl": round(realized, 2), "timestamp": signal["timestamp"]}
            )
            pos.qty = 0
            self.positions[symbol] = pos

    def registrar_saida_por_risco(self, symbol: str, evento: dict):
        """Espelha no trade_log uma saída disparada pelo GestorDeRisco
        (stop, trailing ou alvo), fora do fluxo normal de sinal técnico."""
        pos = self.positions.get(symbol)
        if not pos or pos.qty == 0:
            return
        self.cash += evento["pnl"]
        self.trade_log.append(
            {"symbol": symbol, "action": evento["motivo"], "price": evento["preco_saida"],
             "qty": pos.qty, "realized_pnl": evento["pnl"]}
        )
        pos.qty = 0
        self.positions[symbol] = pos

    def summary(self):
        return {
            "cash_realized_pnl": round(self.cash, 2),
            "exposicao_atual": round(self._exposure_value(), 2),
            "open_positions": {
                s: {"qty": p.qty, "avg_price": round(p.avg_price, 2),
                    "stop_loss": p.stop_loss, "take_profit": p.take_profit}
                for s, p in self.positions.items() if p.qty != 0
            },
            "trades": len(self.trade_log),
        }

"""Portfólio simulado (paper trading). Não envia nenhuma ordem real."""

from dataclasses import dataclass, field
from risk_manager import RiskConfig, calc_position_size, check_exposure_limit


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
    risk_config: RiskConfig = field(default_factory=RiskConfig)

    def _exposure_value(self) -> float:
        return sum(p.qty * p.avg_price for p in self.positions.values() if p.qty > 0)

    def apply_signal(self, symbol: str, signal: dict):
        action = signal["signal"]
        price = signal.get("price")
        if action == "HOLD" or price is None:
            return

        pos = self.positions.get(symbol, Position(symbol))

        if action == "BUY":
            exposicao_atual = self._exposure_value()
            limite = self.risk_config.capital_total * (self.risk_config.exposicao_maxima_pct / 100)
            espaco_restante = limite - exposicao_atual

            if espaco_restante <= 0:
                self.trade_log.append(
                    {"symbol": symbol, "action": "BUY_REJECTED", "price": price,
                     "realized_pnl": 0.0, "motivo": "limite de exposição total atingido",
                     "timestamp": signal["timestamp"]}
                )
                return

            sizing = calc_position_size(price, signal.get("rsi", 50), self.risk_config)
            qty_max_pelo_limite = int(espaco_restante / price)
            qty = min(sizing["qty"], qty_max_pelo_limite)
            if qty == 0:
                return

            pos.avg_price = (
                (pos.avg_price * pos.qty + price * qty) / (pos.qty + qty)
                if pos.qty > 0 else price
            )
            pos.qty += qty
            pos.stop_loss = sizing["stop_loss_price"]
            pos.take_profit = sizing["take_profit_price"]

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

    def check_stops(self, symbol: str, current_price: float):
        """Chamar a cada novo preço pra ver se stop-loss ou take-profit
        foi atingido — dispara saída automática, independente do sinal técnico."""
        pos = self.positions.get(symbol)
        if not pos or pos.qty == 0:
            return None

        if current_price <= pos.stop_loss:
            return self._exit(symbol, pos, current_price, "STOP_LOSS")
        if current_price >= pos.take_profit:
            return self._exit(symbol, pos, current_price, "TAKE_PROFIT")
        return None

    def _exit(self, symbol, pos, price, motivo):
        realized = (price - pos.avg_price) * pos.qty
        self.cash += realized
        self.trade_log.append(
            {"symbol": symbol, "action": motivo, "price": price, "qty": pos.qty,
             "realized_pnl": round(realized, 2)}
        )
        pos.qty = 0
        self.positions[symbol] = pos
        return motivo

    def summary(self):
        return {
            "cash_realized_pnl": round(self.cash, 2),
            "exposicao_atual": round(self._exposure_value(), 2),
            "limite_exposicao": round(
                self.risk_config.capital_total * (self.risk_config.exposicao_maxima_pct / 100), 2
            ),
            "open_positions": {
                s: {"qty": p.qty, "avg_price": round(p.avg_price, 2),
                    "stop_loss": p.stop_loss, "take_profit": p.take_profit}
                for s, p in self.positions.items() if p.qty != 0
            },
            "trades": len(self.trade_log),
        }

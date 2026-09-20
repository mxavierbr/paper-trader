"""
Gestão de risco — módulo independente do resto do projeto (só usa a
biblioteca padrão do Python, nenhum import de outro arquivo do repo).

Decide QUANTO operar, QUANDO sair e QUANDO travar novas entradas.
O sinal técnico/IA decide O QUE operar (BUY/SELL) — este módulo decide
se a entrada é executável dentro do risco aceitável e como ela evolui
depois de aberta.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskConfig:
    risco_por_operacao: float = 1.0          # % do patrimônio arriscado por operação até o stop
    mult_stop_atr: float = 2.0               # distância do stop = ATR * este multiplicador
    mult_alvo_atr: float = 3.0               # distância do alvo = ATR * este multiplicador
    mult_trailing_atr: float = 2.0           # distância do trailing stop em relação à máxima
    exposicao_maxima_ativo: float = 20.0     # % do patrimônio em um único ativo
    exposicao_maxima_setor: float = 35.0     # % do patrimônio em um único setor
    exposicao_maxima_total: float = 80.0     # % do patrimônio em posições abertas ao mesmo tempo
    max_posicoes: int = 8                    # nº máximo de posições abertas simultâneas
    perda_maxima_diaria: float = 3.0         # % do patrimônio — acima disso, trava novas entradas no dia
    drawdown_maximo: float = 15.0            # % de queda do pico do patrimônio — trava até reset manual
    custo_operacao_pct: float = 0.05         # % de custo por ponta (compra OU venda)
    volume_minimo_financeiro: float = 1_000_000.0  # R$ médios negociados/dia abaixo disso, recusa
    participacao_maxima_volume: float = 1.0  # % do volume financeiro médio diário que a ordem pode representar
    relacao_risco_retorno_minima: float = 1.5  # recusa entrada com retorno/risco abaixo disso


@dataclass
class Posicao:
    symbol: str
    setor: str
    qty: int
    preco_entrada: float
    stop: float
    alvo: float
    custo_entrada: float
    maxima_atingida: float = 0.0
    trailing_ativo: bool = False

    def __post_init__(self):
        if self.maxima_atingida <= 0:
            self.maxima_atingida = self.preco_entrada


class GestorDeRisco:
    """Camada de gestão de risco: dimensiona entradas, gerencia stops e
    aplica os circuit breakers de perda diária e drawdown."""

    def __init__(self, config: RiskConfig = None, patrimonio_inicial: float = 100_000.0):
        self.config = config or RiskConfig()
        self.patrimonio_inicial = patrimonio_inicial
        self.caixa = patrimonio_inicial
        self.posicoes: dict[str, Posicao] = {}
        self.last_prices: dict[str, float] = {}
        self.historico_fechadas: list = []

        self.pnl_dia = 0.0
        self.patrimonio_abertura_dia = patrimonio_inicial
        self.patrimonio_maximo = patrimonio_inicial
        self.bloqueio_diario = False
        self.bloqueio_drawdown = False
        self._data_referencia = date.today()

    # ------------------------------------------------------------------
    # Leitura de estado
    # ------------------------------------------------------------------

    def valor_posicao(self, pos: Posicao) -> float:
        preco = self.last_prices.get(pos.symbol, pos.preco_entrada)
        return preco * pos.qty

    def patrimonio(self) -> float:
        return self.caixa + sum(self.valor_posicao(p) for p in self.posicoes.values())

    def _exposicao_ativo(self, symbol: str) -> float:
        pos = self.posicoes.get(symbol)
        return self.valor_posicao(pos) if pos else 0.0

    def _exposicao_setor(self, setor: str) -> float:
        return sum(self.valor_posicao(p) for p in self.posicoes.values() if p.setor == setor)

    def _exposicao_total(self) -> float:
        return sum(self.valor_posicao(p) for p in self.posicoes.values())

    def _drawdown_pct(self) -> float:
        if self.patrimonio_maximo <= 0:
            return 0.0
        queda = self.patrimonio_maximo - self.patrimonio()
        return max(0.0, queda / self.patrimonio_maximo * 100)

    def bloqueado(self) -> bool:
        return self.bloqueio_diario or self.bloqueio_drawdown

    # ------------------------------------------------------------------
    # Entrada
    # ------------------------------------------------------------------

    def avaliar_entrada(self, symbol: str, setor: str, preco: float, atr: float,
                         volume_financeiro_medio: float = None) -> dict:
        """Dimensiona a quantidade pelo risco até o stop e aplica todos os
        tetos de exposição em sequência. Retorna {"aprovado": False, "motivo": ...}
        ou {"aprovado": True, "qty", "stop", "alvo", "relacao_rr"}."""
        cfg = self.config

        if self.bloqueio_diario:
            return {"aprovado": False, "motivo": "perda máxima diária atingida — novas entradas travadas até o próximo dia"}
        if self.bloqueio_drawdown:
            return {"aprovado": False, "motivo": "drawdown máximo atingido — novas entradas travadas até reset manual"}

        if symbol not in self.posicoes and len(self.posicoes) >= cfg.max_posicoes:
            return {"aprovado": False, "motivo": f"limite de {cfg.max_posicoes} posições simultâneas atingido"}

        if preco <= 0:
            return {"aprovado": False, "motivo": "preço inválido"}
        if atr is None or atr <= 0:
            return {"aprovado": False, "motivo": "ATR indisponível — volatilidade não pôde ser medida"}

        if volume_financeiro_medio is not None and volume_financeiro_medio < cfg.volume_minimo_financeiro:
            return {"aprovado": False, "motivo": (
                f"liquidez insuficiente (volume financeiro médio "
                f"{volume_financeiro_medio:,.0f} abaixo do mínimo {cfg.volume_minimo_financeiro:,.0f})"
            )}

        stop = preco - cfg.mult_stop_atr * atr
        alvo = preco + cfg.mult_alvo_atr * atr
        risco_por_unidade = preco - stop
        retorno_por_unidade = alvo - preco

        if risco_por_unidade <= 0:
            return {"aprovado": False, "motivo": "stop calculado acima do preço de entrada"}

        relacao_rr = retorno_por_unidade / risco_por_unidade
        if relacao_rr < cfg.relacao_risco_retorno_minima - 1e-9:
            return {"aprovado": False, "motivo": (
                f"relação risco/retorno {relacao_rr:.2f} abaixo do mínimo "
                f"1:{cfg.relacao_risco_retorno_minima:.1f}"
            )}

        patrimonio = self.patrimonio()

        candidatos = {}

        risco_financeiro_maximo = patrimonio * cfg.risco_por_operacao / 100
        candidatos["risco por operação"] = int(risco_financeiro_maximo / risco_por_unidade)

        espaco_ativo = patrimonio * cfg.exposicao_maxima_ativo / 100 - self._exposicao_ativo(symbol)
        candidatos["exposição máxima por ativo"] = max(0, int(espaco_ativo / preco))

        espaco_setor = patrimonio * cfg.exposicao_maxima_setor / 100 - self._exposicao_setor(setor)
        candidatos["exposição máxima por setor"] = max(0, int(espaco_setor / preco))

        espaco_total = patrimonio * cfg.exposicao_maxima_total / 100 - self._exposicao_total()
        candidatos["exposição máxima total"] = max(0, int(espaco_total / preco))

        if volume_financeiro_medio is not None:
            limite_volume = volume_financeiro_medio * cfg.participacao_maxima_volume / 100
            candidatos["participação máxima no volume"] = max(0, int(limite_volume / preco))

        preco_com_custo = preco * (1 + cfg.custo_operacao_pct / 100)
        candidatos["caixa disponível"] = max(0, int(self.caixa / preco_com_custo))

        motivo_limitante = min(candidatos, key=candidatos.get)
        qty = candidatos[motivo_limitante]

        if qty <= 0:
            return {"aprovado": False, "motivo": f"quantidade zerada pelo teto de {motivo_limitante}"}

        return {
            "aprovado": True,
            "qty": qty,
            "stop": round(stop, 4),
            "alvo": round(alvo, 4),
            "relacao_rr": round(relacao_rr, 2),
            "teto_limitante": motivo_limitante,
        }

    def abrir_posicao(self, symbol: str, setor: str, qty: int, preco: float,
                       stop: float, alvo: float) -> Posicao:
        """Abre uma posição nova, ou reforça (average up/down) uma posição
        já existente no mesmo ativo — soma quantidade, recalcula o preço
        médio de entrada e nunca afrouxa um stop que já subiu por trailing."""
        custo = preco * qty * self.config.custo_operacao_pct / 100
        self.caixa -= preco * qty + custo

        pos = self.posicoes.get(symbol)
        if pos:
            qty_total = pos.qty + qty
            pos.preco_entrada = (pos.preco_entrada * pos.qty + preco * qty) / qty_total
            pos.qty = qty_total
            pos.custo_entrada += custo
            pos.stop = max(pos.stop, stop)
            pos.alvo = alvo
            pos.maxima_atingida = max(pos.maxima_atingida, preco)
        else:
            pos = Posicao(symbol=symbol, setor=setor, qty=qty, preco_entrada=preco,
                          stop=stop, alvo=alvo, custo_entrada=custo)
            self.posicoes[symbol] = pos

        self.last_prices[symbol] = preco
        return pos

    # ------------------------------------------------------------------
    # Acompanhamento e saída
    # ------------------------------------------------------------------

    def atualizar_trailing(self, symbol: str, preco_atual: float, atr: float = None):
        """Sobe o stop conforme o preço avança a favor da posição.
        O stop nunca desce, mesmo que o preço recue."""
        pos = self.posicoes.get(symbol)
        if not pos:
            return

        if preco_atual > pos.maxima_atingida:
            pos.maxima_atingida = preco_atual

        if atr and atr > 0:
            novo_stop = pos.maxima_atingida - self.config.mult_trailing_atr * atr
            if novo_stop > pos.stop:
                pos.stop = novo_stop
                pos.trailing_ativo = True

    def checar_saida(self, symbol: str, preco_atual: float) -> str | None:
        pos = self.posicoes.get(symbol)
        if not pos:
            return None
        if preco_atual <= pos.stop:
            return "TRAILING" if pos.trailing_ativo else "STOP"
        if preco_atual >= pos.alvo:
            return "ALVO"
        return None

    def fechar_posicao(self, symbol: str, preco_atual: float, motivo: str = "MANUAL") -> dict:
        pos = self.posicoes.pop(symbol, None)
        if not pos:
            return {}

        valor_venda = preco_atual * pos.qty
        custo_saida = valor_venda * self.config.custo_operacao_pct / 100
        self.caixa += valor_venda - custo_saida

        pnl = (preco_atual - pos.preco_entrada) * pos.qty - pos.custo_entrada - custo_saida
        self.pnl_dia += pnl
        self.last_prices[symbol] = preco_atual

        registro = {
            "symbol": symbol, "motivo": motivo, "qty": pos.qty,
            "preco_entrada": pos.preco_entrada, "preco_saida": preco_atual,
            "pnl": round(pnl, 2),
        }
        self.historico_fechadas.append(registro)
        return registro

    # ------------------------------------------------------------------
    # Ciclo de cotação
    # ------------------------------------------------------------------

    def _resetar_dia_se_necessario(self):
        hoje = date.today()
        if hoje != self._data_referencia:
            self._data_referencia = hoje
            self.pnl_dia = 0.0
            self.bloqueio_diario = False
            self.patrimonio_abertura_dia = self.patrimonio()

    def _atualizar_circuit_breakers(self):
        if self.patrimonio() > self.patrimonio_maximo:
            self.patrimonio_maximo = self.patrimonio()

        if self._drawdown_pct() >= self.config.drawdown_maximo:
            self.bloqueio_drawdown = True

        if self.patrimonio_abertura_dia > 0:
            perda_dia_pct = -self.pnl_dia / self.patrimonio_abertura_dia * 100
            if perda_dia_pct >= self.config.perda_maxima_diaria:
                self.bloqueio_diario = True

    def processar_precos(self, precos: dict, atrs: dict = None) -> list:
        """Chamar a cada novo ciclo de cotação, antes de avaliar novas
        entradas: atualiza preços, sobe trailing stops e fecha posições
        que bateram stop/alvo. Retorna a lista de saídas disparadas."""
        self._resetar_dia_se_necessario()
        atrs = atrs or {}
        eventos = []

        for symbol, preco in precos.items():
            if preco is None:
                continue
            self.last_prices[symbol] = preco

            if symbol not in self.posicoes:
                continue

            self.atualizar_trailing(symbol, preco, atrs.get(symbol))
            motivo = self.checar_saida(symbol, preco)
            if motivo:
                eventos.append(self.fechar_posicao(symbol, preco, motivo))

        self._atualizar_circuit_breakers()
        return eventos

    def resetar_drawdown(self):
        """Reset manual do circuit breaker de drawdown — precisa de ação
        explícita, não destrava sozinho no dia seguinte como o de perda diária."""
        self.bloqueio_drawdown = False
        self.patrimonio_maximo = self.patrimonio()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        patrimonio = self.patrimonio()
        exposicao_total = self._exposicao_total()

        return {
            "patrimonio": round(patrimonio, 2),
            "caixa": round(self.caixa, 2),
            "exposicao_total": round(exposicao_total, 2),
            "exposicao_total_pct": round(exposicao_total / patrimonio * 100, 2) if patrimonio else 0.0,
            "exposicao_por_setor": {
                setor: round(sum(self.valor_posicao(p) for p in self.posicoes.values() if p.setor == setor), 2)
                for setor in {p.setor for p in self.posicoes.values()}
            },
            "posicoes_abertas": [
                {
                    "symbol": p.symbol, "setor": p.setor, "qty": p.qty,
                    "preco_entrada": round(p.preco_entrada, 2),
                    "preco_atual": round(self.last_prices.get(p.symbol, p.preco_entrada), 2),
                    "stop": round(p.stop, 2), "alvo": round(p.alvo, 2),
                    "trailing_ativo": p.trailing_ativo,
                }
                for p in self.posicoes.values()
            ],
            "num_posicoes_abertas": len(self.posicoes),
            "resultado_do_dia": round(self.pnl_dia, 2),
            "resultado_do_dia_pct": (
                round(self.pnl_dia / self.patrimonio_abertura_dia * 100, 2)
                if self.patrimonio_abertura_dia else 0.0
            ),
            "patrimonio_maximo": round(self.patrimonio_maximo, 2),
            "drawdown_atual_pct": round(self._drawdown_pct(), 2),
            "bloqueio_perda_diaria": self.bloqueio_diario,
            "bloqueio_drawdown": self.bloqueio_drawdown,
            "bloqueado": self.bloqueado(),
        }

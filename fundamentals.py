"""
Camada de dados fundamentalistas — interface plugável.

Para produção, fontes reais:
  - B3 (ações nacionais): brapi.dev cobre balanços (BP, DRE, DFC, DVA)
    padronizados a partir dos dados públicos da CVM — é a fonte mais
    direta pra EMBR3, PETR4, JBSS3 etc.
  - Internacional: Alpha Vantage tem endpoint de fundamentals (EARNINGS,
    INCOME_STATEMENT); a própria IB também expõe fundamentals via API

Hoje: retorna dados fictícios só para validar a integração do pipeline.
"""


class FundamentalsSource:
    def get_fundamentals(self, symbol: str) -> dict:
        raise NotImplementedError


class MockFundamentalsSource(FundamentalsSource):
    """Dados de teste. Nunca usar para decisão real."""

    _SAMPLE = {
        "EMBR3": {
            "setor": "aeroespacial/defesa",
            "periodo": "1S2026",
            "resultado": "prejuízo",
            "receita_var_pct": -12.5,
            "observacao": "queda nas exportações; parte da produção retornou ao mercado interno",
            "sinais_de_risco_contabil": [],  # ex: troca recente de auditoria, dívida crescendo fora do padrão do setor, restatement
        },
        "BBAS3": {
            "setor": "bancário",
            "periodo": "1S2026",
            "resultado": "lucro",
            "receita_var_pct": 4.2,
            "observacao": "setor com regulação e auditoria mais rígida (Bacen) — historicamente menor incidência de fraude contábil relevante",
            "sinais_de_risco_contabil": [],
        },
    }

    def get_fundamentals(self, symbol: str) -> dict:
        return self._SAMPLE.get(symbol, {})


def get_fundamentals_source() -> FundamentalsSource:
    # return BrapiFundamentalsSource()  # trocar quando integrar fonte real (B3)
    # return AlphaVantageFundamentalsSource()  # trocar para símbolos internacionais
    return MockFundamentalsSource()

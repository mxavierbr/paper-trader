"""
Camada de notícias/contexto — interface plugável.

Para produção, fontes reais recomendadas:
  - Fatos Relevantes da CVM/B3 (o mais confiável para "empresa negociando
    contrato grande" — é informação oficial e obrigatória por lei, sai
    antes de virar manchete de jornal)
  - NewsAPI / GNews para notícias gerais em português e inglês
  - Scraping de RI (Relações com Investidores) do site da própria empresa

Hoje: retorna manchetes fictícias, só para testar a integração do
pipeline sem depender de credenciais de API de notícias.
"""


class NewsSource:
    def get_recent_headlines(self, symbol: str) -> list:
        raise NotImplementedError


class MockNewsSource(NewsSource):
    """Gera manchetes de teste. Nunca usar isso para decisão real —
    é só para validar que o pipeline processa e reage a notícias."""

    _SAMPLE = {
        "EMBR3": ["Embraer avança em negociação de contrato internacional de grande porte"],
        "PETR4": ["Petrobras anuncia novo plano de investimento em exploração"],
    }

    def get_recent_headlines(self, symbol: str) -> list:
        return self._SAMPLE.get(symbol, [])


def get_news_source() -> NewsSource:
    # return CVMFatoRelevanteSource()  # trocar quando integrar fonte real
    return MockNewsSource()

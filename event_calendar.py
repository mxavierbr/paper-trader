"""
Calendário de eventos — Copom, Fed, divulgação de balanço. Preço pode
gapear nesses momentos e o stop-loss não funciona como esperado (a
execução pula o preço do stop).

STUB — hoje retorna sempre "sem evento". Fonte real recomendada:
  - Copom/Fed: calendário público do Bacen e do Federal Reserve
  - Balanço: cada empresa publica data de divulgação com antecedência
    (Relações com Investidores / CVM)
"""

from datetime import datetime, timedelta


class EventCalendar:
    def has_upcoming_event(self, symbol: str, within_hours: int = 24) -> dict | None:
        raise NotImplementedError


class MockEventCalendar(EventCalendar):
    def has_upcoming_event(self, symbol: str, within_hours: int = 24) -> dict | None:
        return None  # nenhum evento simulado por padrão


def get_event_calendar() -> EventCalendar:
    return MockEventCalendar()

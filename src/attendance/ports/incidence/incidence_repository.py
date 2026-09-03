"""Puerto IncidenceRepository para justificaciones e incidencias."""

from datetime import date
from typing import Protocol

from attendance.domain.incidence.justification import Justification


class IncidenceRepository(Protocol):
    """Contrato de persistencia para justificaciones e incidencias de asistencia."""

    def save(self, justification: Justification) -> Justification: ...

    def get_by_id(self, justification_id: int) -> Justification | None: ...

    def get_active_justification(
        self, employee_pin: str, target_date: date
    ) -> Justification | None: ...

    def list_by_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Justification]: ...

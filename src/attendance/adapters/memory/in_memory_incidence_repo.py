"""Adaptador en memoria para IncidenceRepository."""

from datetime import date
from typing import Dict

from attendance.domain.incidence.justification import Justification
from attendance.ports.incidence import IncidenceRepository


class InMemoryIncidenceRepository(IncidenceRepository):
    """Implementación en memoria para registrar y consultar justificaciones/incidencias."""

    def __init__(self, initial_records: list[Justification] | None = None) -> None:
        self._records: Dict[int, Justification] = {}
        self._next_id = 1
        if initial_records:
            for j in initial_records:
                self.save(j)

    def save(self, justification: Justification) -> Justification:
        if justification.id is None:
            justification.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, justification.id + 1)
        self._records[justification.id] = justification
        return justification

    def get_by_id(self, justification_id: int) -> Justification | None:
        return self._records.get(justification_id)

    def get_active_justification(
        self, employee_pin: str, target_date: date
    ) -> Justification | None:
        for j in self._records.values():
            if j.employee_pin == employee_pin and j.applies_to_date(target_date):
                return j
        return None

    def list_by_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Justification]:
        results = [
            j for j in self._records.values() if j.employee_pin == employee_pin
        ]
        if start_date is not None:
            results = [j for j in results if j.end_date >= start_date]
        if end_date is not None:
            results = [j for j in results if j.start_date <= end_date]
        return sorted(results, key=lambda j: j.start_date)

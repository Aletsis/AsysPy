"""Adaptador en memoria para ShiftRepository."""

from typing import Dict

from attendance.domain.schedule.shift import ShiftDefinition
from attendance.ports.schedule.shift_repository import ShiftRepository


class InMemoryShiftRepository(ShiftRepository):
    """Implementación en memoria para el catálogo de turnos."""

    def __init__(self, initial_shifts: list[ShiftDefinition] | None = None) -> None:
        self._shifts: Dict[int, ShiftDefinition] = {}
        self._next_id = 1
        if initial_shifts:
            for s in initial_shifts:
                self.save(s)

    def save(self, shift: ShiftDefinition) -> ShiftDefinition:
        if shift.id is None:
            shift.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, shift.id + 1)
        self._shifts[shift.id] = shift
        return shift

    def get_by_id(self, shift_id: int) -> ShiftDefinition | None:
        return self._shifts.get(shift_id)

    def list_all(self) -> list[ShiftDefinition]:
        return list(self._shifts.values())

    def delete(self, shift_id: int) -> bool:
        if shift_id in self._shifts:
            del self._shifts[shift_id]
            return True
        return False

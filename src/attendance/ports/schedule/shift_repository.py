"""Puerto ShiftRepository para catálogo y persistencia de turnos de trabajo."""

from typing import Protocol

from attendance.domain.schedule.shift import ShiftDefinition


class ShiftRepository(Protocol):
    """Contrato de persistencia para el catálogo de turnos."""

    def save(self, shift: ShiftDefinition) -> ShiftDefinition: ...

    def get_by_id(self, shift_id: int) -> ShiftDefinition | None: ...

    def list_all(self) -> list[ShiftDefinition]: ...

    def delete(self, shift_id: int) -> bool: ...

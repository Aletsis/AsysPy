from typing import Protocol

from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position


class PositionRepository(Protocol):
    """Contrato de persistencia y catálogo para puestos o cargos laborales."""

    def save(self, position: Position) -> Position: ...

    def get_by_id(self, position_id: int) -> Position | None: ...

    def get_by_code(self, code: str) -> Position | None: ...

    def list_all(
        self, department_id: int | None = None, active_only: bool = False
    ) -> list[Position]: ...

    def delete(self, position_id: int) -> bool: ...

    def get_departments(
        self, position_id: int, active_only: bool = False
    ) -> list[Department]: ...

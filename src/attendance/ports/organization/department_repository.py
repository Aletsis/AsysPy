from typing import Protocol

from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position


class DepartmentRepository(Protocol):
    """Contrato de persistencia y catálogo para departamentos."""

    def save(self, department: Department) -> Department: ...

    def get_by_id(self, department_id: int) -> Department | None: ...

    def get_by_code(self, code: str) -> Department | None: ...

    def list_all(
        self, branch_id: int | None = None, active_only: bool = False
    ) -> list[Department]: ...

    def delete(self, department_id: int) -> bool: ...

    def assign_position(self, department_id: int, position_id: int) -> None: ...

    def remove_position(self, department_id: int, position_id: int) -> bool: ...

    def get_positions(
        self, department_id: int, active_only: bool = False
    ) -> list[Position]: ...

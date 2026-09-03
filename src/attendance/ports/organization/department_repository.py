"""Puerto DepartmentRepository para persistencia y consulta de departamentos."""

from typing import Protocol

from attendance.domain.organization.department import Department


class DepartmentRepository(Protocol):
    """Contrato de persistencia y catálogo para departamentos."""

    def save(self, department: Department) -> Department: ...

    def get_by_id(self, department_id: int) -> Department | None: ...

    def get_by_code(self, code: str) -> Department | None: ...

    def list_all(
        self, branch_id: int | None = None, active_only: bool = False
    ) -> list[Department]: ...

    def delete(self, department_id: int) -> bool: ...

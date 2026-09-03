"""Implementación en memoria de DepartmentRepository."""

from attendance.domain.organization.department import Department
from attendance.ports.organization.department_repository import DepartmentRepository


class InMemoryDepartmentRepository(DepartmentRepository):
    """Repositorio en memoria para Department."""

    def __init__(self, initial_departments: list[Department] | None = None) -> None:
        self._departments: dict[int, Department] = {}
        self._next_id = 1
        if initial_departments:
            for d in initial_departments:
                self.save(d)

    def save(self, department: Department) -> Department:
        # Si no tiene ID pero coincide el código con uno existente, actualizarlo
        if department.id is None and department.code:
            existing = self.get_by_code(department.code)
            if existing and existing.id is not None:
                department.id = existing.id

        if department.id is None:
            department.id = self._next_id
            self._next_id += 1

        self._departments[department.id] = department
        return department

    def get_by_id(self, department_id: int) -> Department | None:
        return self._departments.get(department_id)

    def get_by_code(self, code: str) -> Department | None:
        for d in self._departments.values():
            if d.code == code:
                return d
        return None

    def list_all(
        self, branch_id: int | None = None, active_only: bool = False
    ) -> list[Department]:
        result = list(self._departments.values())
        if branch_id is not None:
            result = [d for d in result if d.branch_id == branch_id]
        if active_only:
            result = [d for d in result if d.active]
        return result

    def delete(self, department_id: int) -> bool:
        if department_id in self._departments:
            del self._departments[department_id]
            return True
        return False

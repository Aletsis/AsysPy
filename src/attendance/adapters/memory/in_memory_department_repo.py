"""Implementación en memoria de DepartmentRepository."""

from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position
from attendance.ports.organization.department_repository import DepartmentRepository
from attendance.ports.organization.position_repository import PositionRepository


class InMemoryDepartmentRepository(DepartmentRepository):
    """Repositorio en memoria para Department con soporte N:M de puestos."""

    def __init__(
        self,
        initial_departments: list[Department] | None = None,
        position_repo: PositionRepository | None = None,
    ) -> None:
        self._departments: dict[int, Department] = {}
        self._next_id = 1
        self._positions_by_dept: dict[int, set[int]] = {}
        self.position_repo = position_repo
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
            self._positions_by_dept.pop(department_id, None)
            return True
        return False

    def assign_position(self, department_id: int, position_id: int) -> None:
        """Asocia un puesto a un departamento en memoria."""
        if department_id not in self._positions_by_dept:
            self._positions_by_dept[department_id] = set()
        self._positions_by_dept[department_id].add(position_id)

    def remove_position(self, department_id: int, position_id: int) -> bool:
        """Desvincula un puesto de un departamento en memoria."""
        if department_id in self._positions_by_dept:
            if position_id in self._positions_by_dept[department_id]:
                self._positions_by_dept[department_id].remove(position_id)
                return True
        return False

    def get_positions(
        self, department_id: int, active_only: bool = False
    ) -> list[Position]:
        """Obtiene la lista de puestos asignados a un departamento."""
        pos_ids = self._positions_by_dept.get(department_id, set())
        if not self.position_repo:
            return []
        result: list[Position] = []
        for pid in pos_ids:
            p = self.position_repo.get_by_id(pid)
            if p:
                if active_only and not p.active:
                    continue
                result.append(p)
        return sorted(result, key=lambda x: (x.id or 0))

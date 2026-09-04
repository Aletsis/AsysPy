"""Implementación en memoria de PositionRepository."""

from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position
from attendance.ports.organization.department_repository import DepartmentRepository
from attendance.ports.organization.position_repository import PositionRepository


class InMemoryPositionRepository(PositionRepository):
    """Repositorio en memoria para Position con soporte N:M de departamentos."""

    def __init__(
        self,
        initial_positions: list[Position] | None = None,
        department_repo: DepartmentRepository | None = None,
    ) -> None:
        self._positions: dict[int, Position] = {}
        self._next_id = 1
        self.department_repo = department_repo
        if initial_positions:
            for p in initial_positions:
                self.save(p)

    def save(self, position: Position) -> Position:
        if position.id is None and position.code:
            existing = self.get_by_code(position.code)
            if existing and existing.id is not None:
                position.id = existing.id

        if position.id is None:
            position.id = self._next_id
            self._next_id += 1

        self._positions[position.id] = position
        return position

    def get_by_id(self, position_id: int) -> Position | None:
        return self._positions.get(position_id)

    def get_by_code(self, code: str) -> Position | None:
        for p in self._positions.values():
            if p.code == code:
                return p
        return None

    def list_all(
        self, department_id: int | None = None, active_only: bool = False
    ) -> list[Position]:
        result = list(self._positions.values())
        if department_id is not None:
            if self.department_repo and hasattr(self.department_repo, "_positions_by_dept"):
                allowed_ids = self.department_repo._positions_by_dept.get(department_id, set())
                result = [p for p in result if p.id in allowed_ids]
            else:
                result = []
        if active_only:
            result = [p for p in result if p.active]
        return sorted(result, key=lambda p: (p.id or 0))

    def delete(self, position_id: int) -> bool:
        if position_id in self._positions:
            del self._positions[position_id]
            if self.department_repo and hasattr(self.department_repo, "_positions_by_dept"):
                for pos_set in self.department_repo._positions_by_dept.values():
                    pos_set.discard(position_id)
            return True
        return False

    def get_departments(
        self, position_id: int, active_only: bool = False
    ) -> list[Department]:
        """Obtiene los departamentos donde este puesto está asignado."""
        if not self.department_repo or not hasattr(self.department_repo, "_positions_by_dept"):
            return []
        result: list[Department] = []
        for dept_id, pos_set in self.department_repo._positions_by_dept.items():
            if position_id in pos_set:
                dept = self.department_repo.get_by_id(dept_id)
                if dept:
                    if active_only and not dept.active:
                        continue
                    result.append(dept)
        return sorted(result, key=lambda d: (d.id or 0))

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
        else:
            self._next_id = max(self._next_id, position.id + 1)

        self._positions[position.id] = position
        return position

    def save_all(self, positions: list[Position]) -> list[Position]:
        return [self.save(p) for p in positions]

    def get_by_id(self, position_id: int) -> Position | None:
        return self._positions.get(position_id)

    def get_by_code(self, code: str) -> Position | None:
        cleaned = code.strip().upper()
        if not cleaned:
            return None
        for p in self._positions.values():
            if p.code == cleaned:
                return p
        return None

    def get_by_name(self, name: str) -> Position | None:
        cleaned = name.strip().lower()
        if not cleaned:
            return None
        for p in self._positions.values():
            if p.name.strip().lower() == cleaned:
                return p
        return None

    def exists_by_id(self, position_id: int) -> bool:
        return position_id in self._positions

    def exists_by_code(self, code: str) -> bool:
        return self.get_by_code(code) is not None

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
        return sorted(result, key=lambda p: (p.name.lower(), p.id or 0))

    def count(
        self, department_id: int | None = None, active_only: bool = False
    ) -> int:
        return len(self.list_all(department_id=department_id, active_only=active_only))

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

    def assign_department(self, position_id: int, department_id: int) -> None:
        if self.department_repo and hasattr(self.department_repo, "_positions_by_dept"):
            if department_id not in self.department_repo._positions_by_dept:
                self.department_repo._positions_by_dept[department_id] = set()
            self.department_repo._positions_by_dept[department_id].add(position_id)

    def remove_department(self, position_id: int, department_id: int) -> bool:
        if self.department_repo and hasattr(self.department_repo, "_positions_by_dept"):
            if department_id in self.department_repo._positions_by_dept:
                if position_id in self.department_repo._positions_by_dept[department_id]:
                    self.department_repo._positions_by_dept[department_id].remove(position_id)
                    return True
        return False

"""Adaptador en memoria para RotationPatternRepository."""

from typing import Dict

from attendance.domain.schedule.rotation import RotationPattern
from attendance.ports.schedule.rotation_pattern_repository import RotationPatternRepository


class InMemoryRotationPatternRepository(RotationPatternRepository):
    """Implementación en memoria para el catálogo de patrones de rotación."""

    def __init__(
        self, initial_patterns: list[RotationPattern] | None = None
    ) -> None:
        self._patterns: Dict[int, RotationPattern] = {}
        self._next_id = 1
        if initial_patterns:
            for p in initial_patterns:
                self.save(p)

    def save(self, pattern: RotationPattern) -> RotationPattern:
        if pattern.id is None:
            pattern.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, pattern.id + 1)
        self._patterns[pattern.id] = pattern
        return pattern

    def get_by_id(self, pattern_id: int) -> RotationPattern | None:
        return self._patterns.get(pattern_id)

    def list_all(self) -> list[RotationPattern]:
        return list(self._patterns.values())

    def delete(self, pattern_id: int) -> bool:
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            return True
        return False

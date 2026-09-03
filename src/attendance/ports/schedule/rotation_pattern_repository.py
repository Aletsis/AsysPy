"""Puerto RotationPatternRepository para catálogo y persistencia de patrones de rotación."""

from typing import Protocol

from attendance.domain.schedule.rotation import RotationPattern


class RotationPatternRepository(Protocol):
    """Contrato de persistencia para patrones de rotación cíclicos."""

    def save(self, pattern: RotationPattern) -> RotationPattern: ...

    def get_by_id(self, pattern_id: int) -> RotationPattern | None: ...

    def list_all(self) -> list[RotationPattern]: ...

    def delete(self, pattern_id: int) -> bool: ...

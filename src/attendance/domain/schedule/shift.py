"""Entidad ShiftDefinition y Value Object ShiftSegment para turnos regulares y partidos."""

from dataclasses import dataclass, field
from datetime import time

from attendance.domain.common.exceptions import ShiftValidationError
from attendance.domain.common.time_range import TimeRange

from .enums import ShiftCategory


@dataclass(frozen=True)
class ShiftSegment:
    """Segmento horario de trabajo dentro de un turno (útil para turnos partidos)."""

    start_time: time
    end_time: time
    crosses_midnight: bool = False
    tolerance_minutes: int = 0
    name: str = "Segmento"

    def __post_init__(self) -> None:
        if self.tolerance_minutes < 0:
            raise ShiftValidationError("La tolerancia no puede ser negativa.")
        # Validación de rango usando TimeRange
        time_range = TimeRange(self.start_time, self.end_time, self.crosses_midnight)
        if time_range.crosses_midnight != self.crosses_midnight:
            object.__setattr__(self, "crosses_midnight", time_range.crosses_midnight)

    @property
    def duration_minutes(self) -> int:
        return TimeRange(self.start_time, self.end_time, self.crosses_midnight).duration_minutes

    def calculate_tardiness(self, punch_time: time) -> int:
        """Calcula los minutos de retraso respecto a start_time considerando tolerancia."""
        punch_min = punch_time.hour * 60 + punch_time.minute
        start_min = self.start_time.hour * 60 + self.start_time.minute

        # Si el turno cruza medianoche y la marcación fue antes de medianoche
        diff = punch_min - start_min
        if diff <= self.tolerance_minutes:
            return 0
        return diff


@dataclass
class ShiftDefinition:
    """Plantilla de turno reutilizable. Soporta turnos continuos y turnos partidos."""

    id: int | None
    name: str
    category: ShiftCategory = ShiftCategory.PERSONALIZADO
    start_time: time | None = None
    end_time: time | None = None
    tolerance_minutes: int = 0
    crosses_midnight: bool = False
    segments: list[ShiftSegment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.tolerance_minutes < 0:
            raise ShiftValidationError("La tolerancia en minutos no puede ser negativa.")

        # Si se definieron start_time y end_time directamente y no hay segments, creamos el segmento por defecto
        if self.start_time is not None and self.end_time is not None:
            if not self.segments:
                inferred_cross = self.end_time < self.start_time
                if inferred_cross and not self.crosses_midnight:
                    self.crosses_midnight = True
                self.segments = [
                    ShiftSegment(
                        start_time=self.start_time,
                        end_time=self.end_time,
                        crosses_midnight=self.crosses_midnight,
                        tolerance_minutes=self.tolerance_minutes,
                        name=self.name,
                    )
                ]
        elif self.segments:
            # Si se proporcionaron segmentos, sincronizamos start_time y end_time con el primer y último segmento
            self.start_time = self.segments[0].start_time
            self.end_time = self.segments[-1].end_time
            self.crosses_midnight = any(s.crosses_midnight for s in self.segments)
            if self.tolerance_minutes == 0 and self.segments[0].tolerance_minutes > 0:
                self.tolerance_minutes = self.segments[0].tolerance_minutes

    @property
    def is_split(self) -> bool:
        """Indica si es un turno partido (dos o más segmentos de trabajo con descanso intermedio)."""
        return len(self.segments) > 1

    @property
    def expected_work_minutes(self) -> int:
        """Total de minutos netos programados de trabajo en el turno."""
        return sum(s.duration_minutes for s in self.segments)

    def calculate_first_segment_tardiness(self, check_in_time: time) -> int:
        """Calcula minutos de tardanza en la primera entrada del día."""
        if not self.segments:
            return 0
        return self.segments[0].calculate_tardiness(check_in_time)

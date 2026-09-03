"""Entidad RotationPattern para turnos rotativos cíclicos."""

from dataclasses import dataclass
from datetime import date

from .enums import RotationFrequency


@dataclass
class RotationPattern:
    """Patrón de rotación cíclica de turnos (ej. 6x1, rotación semanal de turnos, etc.)."""

    id: int
    name: str
    shift_sequence: list[int | None]  # None representa día de descanso dentro de la secuencia
    frequency: RotationFrequency
    anchor_date: date

    def count_periods_elapsed(self, target_date: date) -> int:
        """Calcula el número de periodos transcurridos desde la fecha ancla hasta target_date."""
        days_elapsed = (target_date - self.anchor_date).days

        if self.frequency == RotationFrequency.DAILY:
            return days_elapsed
        if self.frequency == RotationFrequency.WEEKLY:
            return days_elapsed // 7
        if self.frequency == RotationFrequency.BIWEEKLY:
            return days_elapsed // 14
        if self.frequency == RotationFrequency.MONTHLY:
            months = (target_date.year - self.anchor_date.year) * 12 + (
                target_date.month - self.anchor_date.month
            )
            if target_date.day < self.anchor_date.day:
                months -= 1
            return months

        raise ValueError(f"Frecuencia no soportada: {self.frequency}")

    def resolve_shift_id(self, target_date: date) -> int | None:
        """Devuelve el shift_id correspondiente a la fecha dada, o None si es descanso."""
        periods_elapsed = self.count_periods_elapsed(target_date)
        index = periods_elapsed % len(self.shift_sequence)
        return self.shift_sequence[index]

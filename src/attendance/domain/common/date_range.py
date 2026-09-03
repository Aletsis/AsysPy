"""Value Object DateRange para periodos de vigencia y calendarios."""

from dataclasses import dataclass
from datetime import date

from .exceptions import DateRangeError


@dataclass(frozen=True)
class DateRange:
    """Rango de fechas para vigencias de contratos, políticas, turnos y asignaciones."""

    valid_from: date
    valid_until: date | None = None

    def __post_init__(self) -> None:
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise DateRangeError(
                f"valid_until ({self.valid_until}) no puede ser anterior a valid_from ({self.valid_from})."
            )

    def contains(self, target_date: date) -> bool:
        """Verifica si la fecha dada está dentro de la vigencia."""
        if target_date < self.valid_from:
            return False
        if self.valid_until is not None and target_date > self.valid_until:
            return False
        return True

    def overlaps(self, other: "DateRange") -> bool:
        """Verifica si dos rangos se solapan en algún día."""
        self_end = self.valid_until or date.max
        other_end = other.valid_until or date.max
        return self.valid_from <= other_end and other.valid_from <= self_end

    @property
    def is_open_ended(self) -> bool:
        """Indica si el rango tiene vigencia indefinida."""
        return self.valid_until is None

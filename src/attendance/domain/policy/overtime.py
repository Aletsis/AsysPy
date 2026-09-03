"""Entidad OvertimePolicy y asignaciones de política a empleados."""

from dataclasses import dataclass
from datetime import date

from attendance.domain.common.date_range import DateRange
from attendance.domain.common.exceptions import PolicyViolationError

from .enums import RoundingMethod


@dataclass
class OvertimePolicy:
    """Política de cálculo, redondeo y topes de horas extras."""

    id: int
    name: str
    overtime_allowed: bool = True
    rounding_method: RoundingMethod = RoundingMethod.NONE
    rounding_interval_minutes: int = 15
    daily_cap_minutes: int | None = None
    weekly_cap_minutes: int | None = None
    minimum_minutes_for_overtime: int = 0  # umbral mínimo para que comience a contar

    def __post_init__(self) -> None:
        if self.rounding_interval_minutes < 1:
            raise PolicyViolationError("El intervalo de redondeo debe ser de al menos 1 minuto.")
        if self.daily_cap_minutes is not None and self.daily_cap_minutes < 0:
            raise PolicyViolationError("El tope diario de horas extras no puede ser negativo.")

    def calculate_effective_overtime(self, raw_overtime_minutes: int) -> int:
        """Calcula los minutos de tiempo extra efectivos aplicando umbral, redondeo y topes."""
        if not self.overtime_allowed or raw_overtime_minutes <= 0:
            return 0

        if raw_overtime_minutes < self.minimum_minutes_for_overtime:
            return 0

        rounded = self._apply_rounding(raw_overtime_minutes)

        if self.daily_cap_minutes is not None:
            rounded = min(rounded, self.daily_cap_minutes)

        return rounded

    def _apply_rounding(self, minutes: int) -> int:
        if self.rounding_method == RoundingMethod.NONE or self.rounding_interval_minutes <= 1:
            return minutes

        interval = self.rounding_interval_minutes
        if self.rounding_method == RoundingMethod.ROUND_DOWN:
            return (minutes // interval) * interval
        if self.rounding_method == RoundingMethod.ROUND_UP:
            remainder = minutes % interval
            return minutes if remainder == 0 else minutes + (interval - remainder)
        if self.rounding_method == RoundingMethod.NEAREST:
            remainder = minutes % interval
            if remainder >= (interval / 2):
                return minutes + (interval - remainder)
            return minutes - remainder

        return minutes


@dataclass
class EmployeeOvertimePolicyAssignment:
    """Asignación de una política de tiempo extra a un empleado en un rango de fechas."""

    employee_pin: str
    policy_id: int
    valid_from: date
    valid_until: date | None = None

    def __post_init__(self) -> None:
        DateRange(self.valid_from, self.valid_until)

    def is_active_on(self, target_date: date) -> bool:
        return DateRange(self.valid_from, self.valid_until).contains(target_date)

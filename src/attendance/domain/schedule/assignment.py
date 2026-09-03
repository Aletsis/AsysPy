"""Entidad EmployeeScheduleAssignment para asignaciones de horarios."""

from dataclasses import dataclass
from datetime import date

from attendance.domain.common.date_range import DateRange

from .enums import AssignmentMode, Weekday


@dataclass
class EmployeeScheduleAssignment:
    """Asignación de esquema de horario a un empleado para un rango de fechas."""

    id: int | None
    employee_pin: str
    mode: AssignmentMode
    valid_from: date
    valid_until: date | None = None
    working_weekdays: set[Weekday] | None = (
        None  # None = todos los días son potencialmente laborales
    )
    shift_definition_id: int | None = None  # requerido si mode == FIXED
    rotation_pattern_id: int | None = None  # requerido si mode == ROTATING
    expected_min_sessions: int | None = None  # usado si mode == OPEN

    def __post_init__(self) -> None:
        # Validar consistencia del rango de fechas
        DateRange(self.valid_from, self.valid_until)

    def is_active_on(self, target_date: date) -> bool:
        """Verifica si la asignación está activa en la fecha especificada."""
        return DateRange(self.valid_from, self.valid_until).contains(target_date)

    def is_working_weekday(self, target_date: date) -> bool:
        """Verifica si el día de la semana corresponde a un día laborable según el esquema."""
        if self.working_weekdays is not None:
            return Weekday(target_date.weekday()) in self.working_weekdays
        return True

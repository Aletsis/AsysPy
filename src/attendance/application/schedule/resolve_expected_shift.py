"""Caso de uso para resolver el turno esperado de un empleado en una fecha."""

from datetime import date

from attendance.domain.schedule import (
    RotationPattern,
    ScheduleException,
    ScheduleResolution,
    ScheduleResolver,
    ShiftDefinition,
)
from attendance.ports.schedule import (
    EmployeeScheduleAssignmentRepository,
)


def resolve_expected_shift(
    employee_pin: str,
    target_date: date,
    exceptions: list[ScheduleException],
    assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definitions: dict[int, ShiftDefinition],
    rotation_patterns: dict[int, RotationPattern],
) -> ScheduleResolution:
    """Caso de uso: obtiene la asignación activa y delega al servicio de dominio ScheduleResolver."""
    active_assignment = assignment_repo.get_active_assignment(employee_pin, as_of=target_date)
    return ScheduleResolver.resolve(
        employee_pin=employee_pin,
        target_date=target_date,
        exceptions=exceptions,
        active_assignment=active_assignment,
        shift_definitions=shift_definitions,
        rotation_patterns=rotation_patterns,
    )

"""Caso de uso para asignar esquemas de horario a un empleado."""

from datetime import date, timedelta

from attendance.domain.schedule import (
    AssignmentMode,
    EmployeeScheduleAssignment,
    Weekday,
)
from attendance.ports.schedule import (
    EmployeeScheduleAssignmentRepository,
)


def assign_schedule_to_employee(
    employee_pin: str,
    mode: AssignmentMode,
    valid_from: date,
    assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definition_id: int | None = None,
    rotation_pattern_id: int | None = None,
    expected_min_sessions: int | None = None,
    working_weekdays: set[Weekday] | None = None,
) -> EmployeeScheduleAssignment:
    """Asigna un nuevo esquema de horario a un empleado cerrando la vigencia del anterior si existe."""
    current = assignment_repo.get_active_assignment(employee_pin, as_of=valid_from)
    if current is not None and current.id is not None:
        assignment_repo.close_assignment(current.id, valid_until=valid_from - timedelta(days=1))

    new_assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin=employee_pin,
        mode=mode,
        valid_from=valid_from,
        valid_until=None,
        working_weekdays=working_weekdays,
        shift_definition_id=shift_definition_id,
        rotation_pattern_id=rotation_pattern_id,
        expected_min_sessions=expected_min_sessions,
    )
    return assignment_repo.save(new_assignment)

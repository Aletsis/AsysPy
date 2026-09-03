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
    RotationPatternRepository,
    ShiftRepository,
)


def resolve_expected_shift(
    employee_pin: str,
    target_date: date,
    exceptions: list[ScheduleException],
    assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definitions: dict[int, ShiftDefinition] | None = None,
    rotation_patterns: dict[int, RotationPattern] | None = None,
    shift_repo: ShiftRepository | None = None,
    rotation_pattern_repo: RotationPatternRepository | None = None,
) -> ScheduleResolution:
    """Caso de uso: obtiene la asignación activa y delega al servicio de dominio ScheduleResolver."""
    active_assignment = assignment_repo.get_active_assignment(employee_pin, as_of=target_date)

    shift_dict = dict(shift_definitions or {})
    rot_dict = dict(rotation_patterns or {})

    if active_assignment is not None:
        if (
            active_assignment.shift_definition_id is not None
            and active_assignment.shift_definition_id not in shift_dict
            and shift_repo is not None
        ):
            s = shift_repo.get_by_id(active_assignment.shift_definition_id)
            if s is not None and s.id is not None:
                shift_dict[s.id] = s

        if (
            active_assignment.rotation_pattern_id is not None
            and active_assignment.rotation_pattern_id not in rot_dict
            and rotation_pattern_repo is not None
        ):
            r = rotation_pattern_repo.get_by_id(active_assignment.rotation_pattern_id)
            if r is not None and r.id is not None:
                rot_dict[r.id] = r
                if shift_repo is not None:
                    for s_id in r.shift_sequence:
                        if s_id is not None and s_id not in shift_dict:
                            s = shift_repo.get_by_id(s_id)
                            if s is not None and s.id is not None:
                                shift_dict[s.id] = s

    if shift_repo is not None:
        for exc in exceptions:
            if exc.shift_definition_id is not None and exc.shift_definition_id not in shift_dict:
                s = shift_repo.get_by_id(exc.shift_definition_id)
                if s is not None and s.id is not None:
                    shift_dict[s.id] = s

    return ScheduleResolver.resolve(
        employee_pin=employee_pin,
        target_date=target_date,
        exceptions=exceptions,
        active_assignment=active_assignment,
        shift_definitions=shift_dict,
        rotation_patterns=rot_dict,
    )


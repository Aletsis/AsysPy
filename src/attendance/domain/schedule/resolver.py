"""Servicio de dominio ScheduleResolver y Value Object ScheduleResolution."""

from dataclasses import dataclass
from datetime import date

from .assignment import EmployeeScheduleAssignment
from .enums import AssignmentMode, ScheduleKind
from .exception import ScheduleException
from .rotation import RotationPattern
from .shift import ShiftDefinition


@dataclass
class ScheduleResolution:
    """Resultado de la resolución del turno esperado para un empleado en una fecha."""

    kind: ScheduleKind
    shift_definition: ShiftDefinition | None = None


class ScheduleResolver:
    """Servicio de Dominio que calcula qué turno le corresponde a un empleado en una fecha dada."""

    @staticmethod
    def resolve(
        employee_pin: str,
        target_date: date,
        exceptions: list[ScheduleException],
        active_assignment: EmployeeScheduleAssignment | None,
        shift_definitions: dict[int, ShiftDefinition],
        rotation_patterns: dict[int, RotationPattern],
    ) -> ScheduleResolution:
        # 1. Regla de mayor precedencia: Excepciones explícitas de calendario
        exception = next(
            (e for e in exceptions if e.employee_pin == employee_pin and e.date == target_date),
            None,
        )
        if exception is not None:
            if exception.shift_definition_id is None:
                return ScheduleResolution(kind=ScheduleKind.OFF)
            return ScheduleResolution(
                kind=ScheduleKind.FIXED,
                shift_definition=shift_definitions[exception.shift_definition_id],
            )

        # 2. Sin asignación activa -> día libre
        if active_assignment is None:
            return ScheduleResolution(kind=ScheduleKind.OFF)

        # 3. Verificar si el día de la semana es laborable según el esquema
        if not active_assignment.is_working_weekday(target_date):
            return ScheduleResolution(kind=ScheduleKind.OFF)

        # 4. Esquema Abierto / Flexible (sin horario rígido esperado)
        if active_assignment.mode == AssignmentMode.OPEN:
            return ScheduleResolution(kind=ScheduleKind.OPEN)

        # 5. Esquema Fijo
        if active_assignment.mode == AssignmentMode.FIXED:
            if active_assignment.shift_definition_id is None:
                return ScheduleResolution(kind=ScheduleKind.OFF)
            return ScheduleResolution(
                kind=ScheduleKind.FIXED,
                shift_definition=shift_definitions[active_assignment.shift_definition_id],
            )

        # 6. Esquema Rotativo
        if active_assignment.mode == AssignmentMode.ROTATING:
            if active_assignment.rotation_pattern_id is None:
                return ScheduleResolution(kind=ScheduleKind.OFF)
            pattern = rotation_patterns[active_assignment.rotation_pattern_id]
            resolved_shift_id = pattern.resolve_shift_id(target_date)
            if resolved_shift_id is None:
                return ScheduleResolution(kind=ScheduleKind.OFF)
            return ScheduleResolution(
                kind=ScheduleKind.FIXED,
                shift_definition=shift_definitions[resolved_shift_id],
            )

        raise ValueError(f"Modo de asignación no soportado: {active_assignment.mode}")

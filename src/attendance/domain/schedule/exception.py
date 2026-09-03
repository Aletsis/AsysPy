"""Entidad ScheduleException para excepciones de horario individuales."""

from dataclasses import dataclass
from datetime import date


@dataclass
class ScheduleException:
    """Excepción específica en el horario de un empleado para una fecha puntual.

    Si shift_definition_id es None, fuerza descanso obligatorio (día libre forzado).
    Si tiene un id, fuerza ese turno específico sobreescribiendo el turno asignado.
    """

    employee_pin: str
    date: date
    shift_definition_id: int | None
    reason: str | None = None

"""Casos de uso para gestionar excepciones y eventualidades de horario."""

from datetime import date

from attendance.domain.schedule.exception import ScheduleException
from attendance.ports.schedule.schedule_exception_repository import ScheduleExceptionRepository


def create_schedule_exception(
    employee_pin: str,
    target_date: date,
    exception_repo: ScheduleExceptionRepository,
    shift_definition_id: int | None = None,
    reason: str | None = None,
) -> ScheduleException:
    """Registra una excepción/eventualidad de horario para un colaborador en una fecha puntual.

    Si shift_definition_id es None, fuerza un día de descanso (OFF).
    Si se provee shift_definition_id, fuerza ese turno específico sustituyendo el habitual.
    """
    exception = ScheduleException(
        id=None,
        employee_pin=employee_pin,
        date=target_date,
        shift_definition_id=shift_definition_id,
        reason=reason,
    )
    return exception_repo.save(exception)


def list_schedule_exceptions(
    exception_repo: ScheduleExceptionRepository,
    employee_pin: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ScheduleException]:
    """Consulta las excepciones de horario registradas aplicando filtros opcionales."""
    if employee_pin:
        return exception_repo.list_for_employee(
            employee_pin=employee_pin, start_date=start_date, end_date=end_date
        )
    return exception_repo.list_all()


def cancel_schedule_exception(
    exception_id: int,
    exception_repo: ScheduleExceptionRepository,
) -> bool:
    """Elimina o revoca una excepción de horario previamente registrada."""
    return exception_repo.delete(exception_id)

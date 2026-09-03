"""Caso de uso para emparejar marcaciones crudas de asistencia en sesiones IN/OUT."""

from attendance.domain.attendance import SessionPairer, WorkSession
from attendance.domain.device import AttendanceLog

DEDUP_WINDOW_MINUTES = 2


def pair_attendance_logs(
    employee_pin: str,
    logs: list[AttendanceLog],
    dedup_window_minutes: int = DEDUP_WINDOW_MINUTES,
) -> list[WorkSession]:
    """Empareja marcaciones crudas de un empleado en sesiones IN/OUT delegando al dominio."""
    return SessionPairer.pair_logs(
        employee_pin=employee_pin,
        logs=logs,
        dedup_window_minutes=dedup_window_minutes,
    )

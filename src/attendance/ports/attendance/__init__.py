"""Puertos para el contexto de asistencia y jornadas."""

from .attendance_repository import AttendanceRepository
from .daily_attendance_repository import DailyAttendanceRepository

__all__ = [
    "AttendanceRepository",
    "DailyAttendanceRepository",
]

"""Agregado Raíz DailyAttendance (Jornada Diaria de Asistencia)."""

from dataclasses import dataclass, field
from datetime import date, datetime

from attendance.domain.schedule.shift import ShiftDefinition

from .enums import AttendanceStatus, SessionType
from .session import WorkSession


@dataclass
class DailyAttendance:
    """Agregado que representa la jornada completa de un empleado en una fecha operativa.

    Consolida todas las sesiones del día (turnos regulares, partidos, salidas a comer, permisos)
    y almacena las métricas oficiales de tiempo trabajado, descansos, retardos y horas extras.
    """

    employee_pin: str
    date: date
    expected_shift: ShiftDefinition | None = None
    sessions: list[WorkSession] = field(default_factory=list)
    status: AttendanceStatus = AttendanceStatus.PRESENT
    first_check_in: datetime | None = None
    last_check_out: datetime | None = None
    tardiness_minutes: int = 0
    early_departure_minutes: int = 0
    total_worked_minutes: int = 0
    total_break_minutes: int = 0
    overtime_minutes: int = 0
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.sessions:
            self.recalculate_totals()

    def add_session(self, session: WorkSession) -> None:
        """Agrega una sesión de trabajo y recalcula los totales."""
        self.sessions.append(session)
        self.recalculate_totals()

    def recalculate_totals(self) -> None:
        """Recalcula las marcas de tiempo y duraciones acumuladas de las sesiones."""
        if not self.sessions:
            self.first_check_in = None
            self.last_check_out = None
            self.total_worked_minutes = 0
            self.total_break_minutes = 0
            return

        sorted_sessions = sorted(self.sessions, key=lambda s: s.check_in)
        self.first_check_in = sorted_sessions[0].check_in
        self.last_check_out = sorted_sessions[-1].check_out

        worked = 0
        breaks = 0
        for s in sorted_sessions:
            if s.session_type in (SessionType.REGULAR_WORK, SessionType.SPLIT_SHIFT_PART):
                worked += s.duration_minutes
            elif s.session_type in (
                SessionType.MEAL_BREAK,
                SessionType.PERMISSION,
                SessionType.OTHER,
            ):
                breaks += s.duration_minutes

        self.total_worked_minutes = worked
        self.total_break_minutes = breaks

    @property
    def has_open_sessions(self) -> bool:
        """Indica si existe alguna sesión que aún no registra salida."""
        return any(s.is_open for s in self.sessions)

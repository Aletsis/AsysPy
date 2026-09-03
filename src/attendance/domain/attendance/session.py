"""Entidad WorkSession para pares de entrada y salida."""

from dataclasses import dataclass
from datetime import datetime

from attendance.domain.common.exceptions import SessionInconsistencyError

from .enums import SessionStatus, SessionType


@dataclass
class WorkSession:
    """Par de entrada/salida derivado de marcaciones crudas (o sesión abierta)."""

    id: int | None
    employee_pin: str
    check_in: datetime
    check_out: datetime | None = None
    check_in_log_id: int | None = None
    check_out_log_id: int | None = None
    check_in_device_id: int | None = None
    check_out_device_id: int | None = None
    session_type: SessionType = SessionType.REGULAR_WORK
    status: SessionStatus = SessionStatus.CLOSED

    def __post_init__(self) -> None:
        if self.check_out is not None:
            if self.check_out < self.check_in:
                raise SessionInconsistencyError(
                    f"check_out ({self.check_out}) no puede ser anterior a check_in ({self.check_in})."
                )
            if self.status == SessionStatus.OPEN:
                self.status = SessionStatus.CLOSED
        else:
            if self.status == SessionStatus.CLOSED:
                self.status = SessionStatus.OPEN

    @property
    def duration_minutes(self) -> int:
        """Duración de la sesión en minutos transcurridos."""
        if self.check_out is None:
            return 0
        seconds = (self.check_out - self.check_in).total_seconds()
        return max(0, int(seconds // 60))

    @property
    def is_closed(self) -> bool:
        return self.check_out is not None and self.status == SessionStatus.CLOSED

    @property
    def is_open(self) -> bool:
        return self.check_out is None or self.status == SessionStatus.OPEN

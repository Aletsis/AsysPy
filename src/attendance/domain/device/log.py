"""Entidad AttendanceLog (Marcación cruda inmutable del reloj)."""

from dataclasses import dataclass
from datetime import datetime

from attendance.domain.common.exceptions import InvalidPunchError

from .enums import AuthMethod, LogStatus


@dataclass
class AttendanceLog:
    """Registro crudo e inmutable de marcación obtenido de un reloj biométrico."""

    id: int | None
    record_uid: int
    employee_pin: str
    device_id: int
    timestamp: datetime
    raw_status: int = 0
    raw_punch: int = 1
    auth_method: AuthMethod = AuthMethod.FINGERPRINT
    processing_status: LogStatus = LogStatus.RAW
    inferred_type: str | None = None

    def __post_init__(self) -> None:
        if not self.employee_pin or not str(self.employee_pin).strip():
            raise InvalidPunchError("La marcación debe contener un employee_pin válido.")
        if self.record_uid < 0:
            raise InvalidPunchError("El record_uid no puede ser negativo.")

    def mark_as_processed(self, inferred_type: str | None = None) -> None:
        self.processing_status = LogStatus.PROCESSED
        if inferred_type:
            self.inferred_type = inferred_type

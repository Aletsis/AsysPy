"""Entidad Justification para registrar ausencias, vacaciones e incidencias justificadas."""

from dataclasses import dataclass, field
from datetime import date, datetime, time

from attendance.domain.common.exceptions import ValidationError

from .enums import JustificationStatus, JustificationType


@dataclass
class Justification:
    """Entidad que representa una justificación formal de ausencia o permiso laboral."""

    id: int | None
    employee_pin: str
    type: JustificationType
    start_date: date
    end_date: date
    reason: str
    approved_by: str | None = None
    status: JustificationStatus = JustificationStatus.APPROVED
    support_document: str | None = None  # Folio IMSS, comprobante, número de oficio
    created_at: datetime = field(default_factory=datetime.now)
    start_time: time | None = None  # Permiso por horas dentro del día
    end_time: time | None = None

    def __post_init__(self) -> None:
        if not self.employee_pin or not str(self.employee_pin).strip():
            raise ValidationError("El PIN de empleado no puede estar vacío.")
        if self.end_date < self.start_date:
            raise ValidationError(
                f"La fecha fin ({self.end_date}) no puede ser anterior a la fecha inicio ({self.start_date})."
            )
        if not self.reason or not self.reason.strip():
            raise ValidationError("El motivo de la justificación no puede estar vacío.")
        if (self.start_time is not None and self.end_time is None) or (
            self.start_time is None and self.end_time is not None
        ):
            raise ValidationError("Debe especificar tanto hora de inicio como fin para permisos por horas.")
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValidationError("La hora de inicio de permiso debe ser menor a la hora de fin.")

    def applies_to_date(self, target_date: date) -> bool:
        """Determina si esta justificación cubre la fecha indicada y está aprobada."""
        return (
            self.status == JustificationStatus.APPROVED
            and self.start_date <= target_date <= self.end_date
        )

    @property
    def is_full_day(self) -> bool:
        """Indica si el permiso o justificación es de jornada completa."""
        return self.start_time is None and self.end_time is None

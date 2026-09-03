"""Entidad AuditLog y Enums para trazabilidad de auditoría en ajustes manuales."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from attendance.domain.common.exceptions import ValidationError


class AuditAction(str, Enum):
    """Acciones auditables sobre marcaciones y jornadas de asistencia."""

    PUNCH_CREATED = "punch_created"  # Creación manual de marcación
    PUNCH_UPDATED = "punch_updated"  # Modificación de fecha/hora de marcación
    PUNCH_DELETED = "punch_deleted"  # Anulación o marcado como ignorado de marcación
    SESSION_ADJUSTED = "session_adjusted"  # Modificación manual de sesión de trabajo
    ATTENDANCE_OVERRIDDEN = "attendance_overridden"  # Sobreescritura manual de estatus de asistencia


@dataclass
class AuditLog:
    """Registro inmutable de trazabilidad de auditoría."""

    id: int | None
    entity_type: str  # Ej: "attendance_log", "work_session", "daily_attendance"
    entity_id: str | int
    action: AuditAction
    performed_by: str  # Identificador o correo del administrador/supervisor
    reason: str  # Motivo obligatorio del ajuste
    timestamp: datetime = field(default_factory=datetime.now)
    previous_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    employee_pin: str | None = None

    def __post_init__(self) -> None:
        if not self.performed_by or not str(self.performed_by).strip():
            raise ValidationError("El usuario que realiza el ajuste auditado es obligatorio.")
        if not self.reason or not str(self.reason).strip():
            raise ValidationError("El motivo o justificación del ajuste de auditoría es obligatorio.")
        if not self.entity_type or not str(self.entity_type).strip():
            raise ValidationError("El tipo de entidad auditada es obligatorio.")

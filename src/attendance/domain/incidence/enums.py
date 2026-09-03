"""Enums para incidencias, permisos y justificaciones de asistencia."""

from enum import Enum


class JustificationType(str, Enum):
    """Tipos de justificaciones de ausencia o incidencias de jornada."""

    VACATION = "vacation"  # Vacaciones
    IMSS_INCAPACITY = "imss_incapacity"  # Incapacidad médica oficial (IMSS / Salud ocupacional)
    PAID_LEAVE = "paid_leave"  # Permiso con goce de sueldo (paternidad, luto, etc.)
    UNPAID_LEAVE = "unpaid_leave"  # Permiso sin goce de sueldo
    COMMISSION = "commission"  # Comisión laboral / trabajo fuera de sede / Home Office
    OTHER = "other"  # Otros permisos o justificaciones autorizadas


class JustificationStatus(str, Enum):
    """Estado de aprobación de la justificación."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

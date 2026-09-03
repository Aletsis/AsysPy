"""Excepciones de dominio para AsistPy."""


class DomainError(Exception):
    """Excepción base para todos los errores de las reglas de negocio/dominio."""


class ValidationError(DomainError):
    """Error al validar invariantes o datos en una entidad o Value Object."""


class ShiftValidationError(ValidationError):
    """Error al configurar un turno (horarios incoherentes, tolerancias negativas, etc.)."""


class TimeRangeError(ValidationError):
    """Error en la definición o cálculo de un rango horario."""


class DateRangeError(ValidationError):
    """Error en un rango de fechas (ej. fecha final anterior a la inicial)."""


class InvalidPunchError(DomainError):
    """Marcación inválida o corrupta del reloj biométrico."""


class SessionInconsistencyError(DomainError):
    """Inconsistencia al construir o manipular una sesión de trabajo."""


class ScheduleConflictError(DomainError):
    """Conflicto en la asignación o resolución de turnos y excepciones."""


class PolicyViolationError(DomainError):
    """Violación de políticas de jornada laboral o de horas extras."""

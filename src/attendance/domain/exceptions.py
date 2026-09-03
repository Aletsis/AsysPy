"""Re-export de excepciones para retrocompatibilidad."""

from attendance.domain.common.exceptions import (
    DateRangeError,
    DomainError,
    InvalidPunchError,
    PolicyViolationError,
    ScheduleConflictError,
    SessionInconsistencyError,
    ShiftValidationError,
    TimeRangeError,
    ValidationError,
)

__all__ = [
    "DateRangeError",
    "DomainError",
    "InvalidPunchError",
    "PolicyViolationError",
    "ScheduleConflictError",
    "SessionInconsistencyError",
    "ShiftValidationError",
    "TimeRangeError",
    "ValidationError",
]

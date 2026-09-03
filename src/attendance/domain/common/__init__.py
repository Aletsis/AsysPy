"""Módulo común de dominio: Value objects genéricos y excepciones."""

from .date_range import DateRange
from .exceptions import (
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
from .time_range import TimeRange

__all__ = [
    "DateRange",
    "DateRangeError",
    "DomainError",
    "InvalidPunchError",
    "PolicyViolationError",
    "ScheduleConflictError",
    "SessionInconsistencyError",
    "ShiftValidationError",
    "TimeRange",
    "TimeRangeError",
    "ValidationError",
]

"""Subdominio de horarios, turnos, rotaciones y asignaciones."""

from .assignment import EmployeeScheduleAssignment
from .enums import (
    AssignmentMode,
    RotationFrequency,
    ScheduleKind,
    ShiftCategory,
    Weekday,
)
from .exception import ScheduleException
from .resolver import ScheduleResolution, ScheduleResolver
from .rotation import RotationPattern
from .shift import ShiftDefinition, ShiftSegment

__all__ = [
    "AssignmentMode",
    "EmployeeScheduleAssignment",
    "RotationFrequency",
    "RotationPattern",
    "ScheduleException",
    "ScheduleKind",
    "ScheduleResolution",
    "ScheduleResolver",
    "ShiftCategory",
    "ShiftDefinition",
    "ShiftSegment",
    "Weekday",
]

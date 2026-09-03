"""Re-export de value objects y enums para retrocompatibilidad."""

from attendance.domain.attendance.enums import (
    AttendanceStatus,
    SessionStatus,
    SessionType,
)
from attendance.domain.common.date_range import DateRange
from attendance.domain.common.time_range import TimeRange
from attendance.domain.device.enums import (
    AuthMethod,
    DeviceProtocol,
    LogStatus,
)
from attendance.domain.policy.enums import RoundingMethod
from attendance.domain.schedule.enums import (
    AssignmentMode,
    RotationFrequency,
    ScheduleKind,
    ShiftCategory,
    Weekday,
)

__all__ = [
    "AssignmentMode",
    "AttendanceStatus",
    "AuthMethod",
    "DateRange",
    "DeviceProtocol",
    "LogStatus",
    "RotationFrequency",
    "RoundingMethod",
    "ScheduleKind",
    "SessionStatus",
    "SessionType",
    "ShiftCategory",
    "TimeRange",
    "Weekday",
]

"""API Pública del Dominio de AsistPy (Arquitectura Hexagonal Modular)."""

# Common
# Attendance
from attendance.domain.attendance import (
    AttendanceEvaluator,
    AttendanceStatus,
    DailyAttendance,
    SessionPairer,
    SessionStatus,
    SessionType,
    WorkSession,
)
from attendance.domain.audit import (
    AuditAction,
    AuditLog,
)
from attendance.domain.common import (
    DateRange,
    DateRangeError,
    DomainError,
    InvalidPunchError,
    PolicyViolationError,
    ScheduleConflictError,
    SessionInconsistencyError,
    ShiftValidationError,
    TimeRange,
    TimeRangeError,
    ValidationError,
)

# Device
from attendance.domain.device import (
    AttendanceLog,
    AuthMethod,
    Device,
    DeviceCapabilities,
    DeviceProtocol,
    LogStatus,
    SyncState,
)
from attendance.domain.incidence import (
    Justification,
    JustificationStatus,
    JustificationType,
)

# Organization
from attendance.domain.organization import (
    Address,
    Branch,
    Department,
    Employee,
    Fingerprint,
    Position,
    Sex,
)

# Policy
from attendance.domain.policy import (
    EmployeeOvertimePolicyAssignment,
    OvertimePolicy,
    RoundingMethod,
)

# Schedule
from attendance.domain.schedule import (
    AssignmentMode,
    EmployeeScheduleAssignment,
    RotationFrequency,
    RotationPattern,
    ScheduleException,
    ScheduleKind,
    ScheduleResolution,
    ScheduleResolver,
    ShiftCategory,
    ShiftDefinition,
    ShiftSegment,
    Weekday,
)

__all__ = [
    # Common
    "DomainError",
    "ValidationError",
    "ShiftValidationError",
    "TimeRangeError",
    "DateRangeError",
    "InvalidPunchError",
    "SessionInconsistencyError",
    "ScheduleConflictError",
    "PolicyViolationError",
    "TimeRange",
    "DateRange",
    # Organization
    "Address",
    "Branch",
    "Department",
    "Employee",
    "Fingerprint",
    "Position",
    "Sex",
    # Schedule
    "ShiftCategory",
    "RotationFrequency",
    "AssignmentMode",
    "ScheduleKind",
    "Weekday",
    "ShiftSegment",
    "ShiftDefinition",
    "RotationPattern",
    "EmployeeScheduleAssignment",
    "ScheduleException",
    "ScheduleResolution",
    "ScheduleResolver",
    # Device
    "DeviceProtocol",
    "AuthMethod",
    "LogStatus",
    "DeviceCapabilities",
    "Device",
    "AttendanceLog",
    "SyncState",
    # Policy
    "RoundingMethod",
    "OvertimePolicy",
    "EmployeeOvertimePolicyAssignment",
    # Attendance
    "SessionType",
    "SessionStatus",
    "AttendanceStatus",
    "WorkSession",
    "DailyAttendance",
    "SessionPairer",
    "AttendanceEvaluator",
    # Incidence
    "JustificationType",
    "JustificationStatus",
    "Justification",
    # Audit
    "AuditAction",
    "AuditLog",
]

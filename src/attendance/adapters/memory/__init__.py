"""Adaptadores en memoria (Fakes / In-Memory Repositories)."""

from .in_memory_attendance_repo import InMemoryAttendanceRepository
from .in_memory_audit_repo import InMemoryAuditLogRepository
from .in_memory_branch_repo import InMemoryBranchRepository
from .in_memory_daily_attendance_repo import InMemoryDailyAttendanceRepository
from .in_memory_department_repo import InMemoryDepartmentRepository
from .in_memory_device_repo import InMemoryDeviceRepository
from .in_memory_employee_repo import InMemoryEmployeeRepository
from .in_memory_incidence_repo import InMemoryIncidenceRepository
from .in_memory_position_repo import InMemoryPositionRepository
from .in_memory_rotation_pattern_repo import (
    InMemoryRotationPatternRepository,
)
from .in_memory_schedule_assignment_repo import (
    InMemoryScheduleAssignmentRepository,
)
from .in_memory_schedule_exception_repo import (
    InMemoryScheduleExceptionRepository,
)
from .in_memory_shift_repo import InMemoryShiftRepository
from .in_memory_sync_state_repo import InMemorySyncStateRepository

__all__ = [
    "InMemoryAttendanceRepository",
    "InMemoryAuditLogRepository",
    "InMemoryBranchRepository",
    "InMemoryDailyAttendanceRepository",
    "InMemoryDepartmentRepository",
    "InMemoryDeviceRepository",
    "InMemoryEmployeeRepository",
    "InMemoryIncidenceRepository",
    "InMemoryPositionRepository",
    "InMemoryRotationPatternRepository",
    "InMemoryScheduleAssignmentRepository",
    "InMemoryScheduleExceptionRepository",
    "InMemoryShiftRepository",
    "InMemorySyncStateRepository",
]

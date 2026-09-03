"""Adaptadores en memoria (Fakes / In-Memory Repositories)."""

from .in_memory_attendance_repo import InMemoryAttendanceRepository
from .in_memory_audit_repo import InMemoryAuditLogRepository
from .in_memory_daily_attendance_repo import InMemoryDailyAttendanceRepository
from .in_memory_device_repo import InMemoryDeviceRepository
from .in_memory_employee_repo import InMemoryEmployeeRepository
from .in_memory_incidence_repo import InMemoryIncidenceRepository
from .in_memory_schedule_assignment_repo import (
    InMemoryScheduleAssignmentRepository,
)
from .in_memory_sync_state_repo import InMemorySyncStateRepository

__all__ = [
    "InMemoryAttendanceRepository",
    "InMemoryAuditLogRepository",
    "InMemoryDailyAttendanceRepository",
    "InMemoryDeviceRepository",
    "InMemoryEmployeeRepository",
    "InMemoryIncidenceRepository",
    "InMemoryScheduleAssignmentRepository",
    "InMemorySyncStateRepository",
]

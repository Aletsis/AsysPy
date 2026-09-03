"""Repositorios de persistencia relacional con SQLAlchemy."""

from attendance.adapters.persistence.sql.repositories.attendance_repo import SqlAttendanceRepository
from attendance.adapters.persistence.sql.repositories.audit_repo import SqlAuditLogRepository
from attendance.adapters.persistence.sql.repositories.branch_repo import SqlBranchRepository
from attendance.adapters.persistence.sql.repositories.daily_attendance_repo import (
    SqlDailyAttendanceRepository,
)
from attendance.adapters.persistence.sql.repositories.department_repo import SqlDepartmentRepository
from attendance.adapters.persistence.sql.repositories.device_repo import SqlDeviceRepository
from attendance.adapters.persistence.sql.repositories.employee_repo import SqlEmployeeRepository
from attendance.adapters.persistence.sql.repositories.incidence_repo import SqlIncidenceRepository
from attendance.adapters.persistence.sql.repositories.rotation_pattern_repo import (
    SqlRotationPatternRepository,
)
from attendance.adapters.persistence.sql.repositories.schedule_assignment_repo import (
    SqlScheduleAssignmentRepository,
)
from attendance.adapters.persistence.sql.repositories.shift_repo import SqlShiftRepository
from attendance.adapters.persistence.sql.repositories.sync_state_repo import SqlSyncStateRepository

__all__ = [
    "SqlAttendanceRepository",
    "SqlAuditLogRepository",
    "SqlBranchRepository",
    "SqlDailyAttendanceRepository",
    "SqlDepartmentRepository",
    "SqlDeviceRepository",
    "SqlEmployeeRepository",
    "SqlIncidenceRepository",
    "SqlRotationPatternRepository",
    "SqlScheduleAssignmentRepository",
    "SqlShiftRepository",
    "SqlSyncStateRepository",
]

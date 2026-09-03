"""Capa de persistencia SQL de AsistPy basada en SQLAlchemy 2.0."""

from attendance.adapters.persistence.sql.database import (
    Database,
    create_db_engine,
    create_session_factory,
    drop_db,
    init_db,
)
from attendance.adapters.persistence.sql.models import (
    Base,
    RotationPatternModel,
    ShiftModel,
)
from attendance.adapters.persistence.sql.repositories import (
    SqlAttendanceRepository,
    SqlAuditLogRepository,
    SqlDailyAttendanceRepository,
    SqlDeviceRepository,
    SqlEmployeeRepository,
    SqlIncidenceRepository,
    SqlRotationPatternRepository,
    SqlScheduleAssignmentRepository,
    SqlShiftRepository,
    SqlSyncStateRepository,
)

__all__ = [
    "Base",
    "Database",
    "create_db_engine",
    "create_session_factory",
    "init_db",
    "drop_db",
    "RotationPatternModel",
    "ShiftModel",
    "SqlAttendanceRepository",
    "SqlAuditLogRepository",
    "SqlDailyAttendanceRepository",
    "SqlDeviceRepository",
    "SqlEmployeeRepository",
    "SqlIncidenceRepository",
    "SqlRotationPatternRepository",
    "SqlScheduleAssignmentRepository",
    "SqlShiftRepository",
    "SqlSyncStateRepository",
]

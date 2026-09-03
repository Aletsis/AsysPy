"""Puertos de arquitectura hexagonal para AsistPy (organizados por submódulos)."""

# Submódulos
from . import attendance, audit, device, incidence, organization, schedule

# Re-exports directos para conveniencia
from .attendance import (
    AttendanceRepository,
    DailyAttendanceRepository,
)
from .audit import (
    AuditLogRepository,
)
from .device import (
    DeviceReader,
    DeviceRegistry,
    SyncStateRepository,
)
from .incidence import (
    IncidenceRepository,
)
from .organization import (
    EmployeeRepository,
)
from .schedule import (
    EmployeeScheduleAssignmentRepository,
)

__all__ = [
    # Submódulos
    "attendance",
    "schedule",
    "device",
    "incidence",
    "organization",
    "audit",
    # Protocolos individuales
    "AttendanceRepository",
    "DailyAttendanceRepository",
    "AuditLogRepository",
    "DeviceReader",
    "DeviceRegistry",
    "SyncStateRepository",
    "EmployeeRepository",
    "EmployeeScheduleAssignmentRepository",
    "IncidenceRepository",
]

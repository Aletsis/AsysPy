"""Capa de aplicación de AsistPy (Casos de Uso organizados por submódulos)."""

# Submódulos
from . import adjustment, attendance, device, incidence, schedule

# Re-exports directos para conveniencia
from .adjustment import (
    cancel_punch,
    create_manual_punch,
    modify_punch_timestamp,
)
from .attendance import (
    ProcessDailyAttendance,
    ProcessDailyAttendanceBatch,
    ProcessEmployeeAttendanceRange,
    pair_attendance_logs,
    process_daily_attendance,
    process_daily_attendance_batch,
    process_employee_attendance_range,
)
from .device import (
    sync_device_logs,
)
from .incidence import (
    cancel_justification,
    register_justification,
)
from .schedule import (
    assign_schedule_to_employee,
    resolve_expected_shift,
)

__all__ = [
    # Submódulos
    "attendance",
    "schedule",
    "device",
    "incidence",
    "adjustment",
    # Clases orquestadoras
    "ProcessDailyAttendance",
    "ProcessEmployeeAttendanceRange",
    "ProcessDailyAttendanceBatch",
    # Asistencia central
    "process_daily_attendance",
    "process_daily_attendance_batch",
    "process_employee_attendance_range",
    "pair_attendance_logs",
    # Horarios
    "assign_schedule_to_employee",
    "resolve_expected_shift",
    # Telemetría de dispositivos
    "sync_device_logs",
    # Incidencias y permisos
    "register_justification",
    "cancel_justification",
    # Ajustes manuales y auditoría
    "create_manual_punch",
    "modify_punch_timestamp",
    "cancel_punch",
]

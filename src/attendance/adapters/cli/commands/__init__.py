"""Comandos de la CLI de AsistPy."""

from .attendance import register_attendance_subparser
from .branch import register_branch_subparser
from .db import register_db_subparser
from .department import register_department_subparser
from .device import register_device_subparser
from .employee import register_employee_subparser
from .position import register_position_subparser
from .report import register_report_subparser
from .schedule import register_schedule_subparser
from .shift import register_shift_subparser
from .worker import register_worker_subparser

__all__ = [
    "register_attendance_subparser",
    "register_branch_subparser",
    "register_db_subparser",
    "register_department_subparser",
    "register_device_subparser",
    "register_employee_subparser",
    "register_position_subparser",
    "register_report_subparser",
    "register_schedule_subparser",
    "register_shift_subparser",
    "register_worker_subparser",
]

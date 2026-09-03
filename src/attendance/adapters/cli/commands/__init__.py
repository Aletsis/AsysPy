"""Comandos de la CLI de AsistPy."""

from .attendance import register_attendance_subparser
from .db import register_db_subparser
from .device import register_device_subparser
from .report import register_report_subparser

__all__ = [
    "register_attendance_subparser",
    "register_db_subparser",
    "register_device_subparser",
    "register_report_subparser",
]

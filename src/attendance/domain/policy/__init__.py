"""Subdominio de políticas laborales y de horas extras."""

from .enums import RoundingMethod
from .overtime import EmployeeOvertimePolicyAssignment, OvertimePolicy

__all__ = [
    "EmployeeOvertimePolicyAssignment",
    "OvertimePolicy",
    "RoundingMethod",
]

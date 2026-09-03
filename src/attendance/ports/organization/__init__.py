"""Puertos para el contexto de organización y empleados."""

from .branch_repository import BranchRepository
from .department_repository import DepartmentRepository
from .employee_repository import EmployeeRepository

__all__ = [
    "BranchRepository",
    "DepartmentRepository",
    "EmployeeRepository",
]

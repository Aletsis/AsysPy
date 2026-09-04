"""Subdominio de estructura organizacional: Empleados, Sucursales y Departamentos."""

from .address import Address
from .branch import Branch
from .department import Department
from .employee import Employee, Sex
from .fingerprint import Fingerprint

__all__ = [
    "Address",
    "Branch",
    "Department",
    "Employee",
    "Fingerprint",
    "Sex",
]

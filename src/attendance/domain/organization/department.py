"""Entidad Department (Departamento)."""

from dataclasses import dataclass


@dataclass
class Department:
    name: str
    id: int | None = None
    code: str | None = None
    branch_id: int | None = None  # None si el departamento aplica a toda la empresa
    active: bool = True

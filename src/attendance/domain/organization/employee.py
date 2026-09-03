"""Entidad Employee y Enums de organización."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from attendance.domain.common.exceptions import ValidationError


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class Employee:
    id: int | None
    pin: str
    first_name: str
    paternal_last_name: str
    maternal_last_name: str | None
    hire_date: date
    sex: Sex
    department_id: int
    position: str
    home_branch_id: int
    active: bool = True

    def __post_init__(self) -> None:
        if not self.pin or not str(self.pin).strip():
            raise ValidationError("El PIN de empleado no puede estar vacío.")
        if not self.first_name or not self.first_name.strip():
            raise ValidationError("El nombre del empleado no puede estar vacío.")
        if not self.paternal_last_name or not self.paternal_last_name.strip():
            raise ValidationError("El apellido paterno del empleado no puede estar vacío.")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.paternal_last_name, self.maternal_last_name]
        return " ".join(p for p in parts if p)

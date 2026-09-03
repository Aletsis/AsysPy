"""Entidad Branch (Sucursal)."""

from dataclasses import dataclass

from .address import Address


@dataclass
class Branch:
    name: str
    code: str
    id: int | None = None
    address: Address | None = None
    timezone: str = "America/Mexico_City"
    active: bool = True

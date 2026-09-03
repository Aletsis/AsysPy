"""Entidad Branch (Sucursal)."""

from dataclasses import dataclass

from .address import Address


@dataclass
class Branch:
    id: int
    name: str
    code: str
    address: Address | None = None
    timezone: str = "America/Mexico_City"
    active: bool = True

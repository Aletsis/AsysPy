"""Value Object Address para sucursales y ubicaciones."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    street: str
    exterior_number: str
    interior_number: str | None
    postal_code: str
    neighborhood: str  # colonia
    municipality: str  # municipio / alcaldía
    state: str
    country: str = "México"

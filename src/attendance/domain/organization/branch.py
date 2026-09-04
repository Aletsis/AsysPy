"""Entidad Branch (Sucursal)."""

import re
from dataclasses import dataclass

from attendance.domain.common.exceptions import ValidationError

from .address import Address

# Expresiones regulares para validaciones de contacto
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
_PHONE_ALLOWED_CHARS = re.compile(r"^\+?[\d\s\-\(\)]+$")


@dataclass
class Branch:
    """Entidad que representa una sucursal, planta u oficina física de la organización."""

    name: str
    code: str
    id: int | None = None
    address: Address | None = None
    timezone: str = "America/Mexico_City"
    active: bool = True
    email: str | None = None
    phone_number: str | None = None

    def __post_init__(self) -> None:
        self._normalize()
        self.validate()

    def _normalize(self) -> None:
        """Normaliza valores de texto antes de la validación."""
        if self.name is not None:
            self.name = str(self.name).strip()

        if self.code is not None:
            cleaned_code = str(self.code).strip().upper()
            self.code = cleaned_code if cleaned_code else ""

        if self.timezone is None:
            self.timezone = "America/Mexico_City"
        else:
            self.timezone = str(self.timezone).strip()

        if self.email is not None:
            cleaned_email = str(self.email).strip().lower()
            self.email = cleaned_email if cleaned_email else ""

        if self.phone_number is not None:
            cleaned_phone = str(self.phone_number).strip()
            self.phone_number = cleaned_phone if cleaned_phone else ""

    def validate(self) -> None:
        """Valida exhaustivamente los atributos de la sucursal."""
        # Validación de ID
        if self.id is not None:
            if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
                raise ValidationError("El ID de sucursal debe ser un número entero positivo.")

        # Validación de Nombre
        if not self.name:
            raise ValidationError("El nombre de la sucursal no puede estar vacío.")
        if len(self.name) > 100:
            raise ValidationError("El nombre de la sucursal no puede exceder los 100 caracteres.")

        # Validación de Código (opcional)
        if self.code is not None:
            if not self.code:
                raise ValidationError("El código de la sucursal no puede estar vacío.")
            if any(c.isspace() for c in self.code):
                raise ValidationError("El código de la sucursal no puede contener espacios en blanco.")
            if len(self.code) > 30:
                raise ValidationError("El código de la sucursal no puede exceder los 30 caracteres.")

        # Validación de Zona Horaria
        if not self.timezone:
            raise ValidationError("La zona horaria de la sucursal no puede estar vacía.")

        # Validación de Dirección (opcional)
        if self.address is not None and not isinstance(self.address, Address):
            raise ValidationError("La dirección de la sucursal debe ser una instancia de Address.")

        # Validación de Estado Activo
        if not isinstance(self.active, bool):
            raise ValidationError("El estado activo de la sucursal debe ser un valor booleano.")

        # Validación de Correo Electrónico (opcional)
        if self.email is not None:
            if not self.email:
                raise ValidationError("El correo electrónico de la sucursal no puede ser una cadena vacía.")
            if len(self.email) > 255:
                raise ValidationError("El correo electrónico de la sucursal no puede exceder los 255 caracteres.")
            if not _EMAIL_REGEX.match(self.email):
                raise ValidationError(f"El formato del correo electrónico de la sucursal es inválido: '{self.email}'.")

        # Validación de Número Telefónico (opcional)
        if self.phone_number is not None:
            if not self.phone_number:
                raise ValidationError("El número de teléfono de la sucursal no puede ser una cadena vacía.")
            if not _PHONE_ALLOWED_CHARS.match(self.phone_number):
                raise ValidationError(
                    f"El número de teléfono '{self.phone_number}' contiene caracteres inválidos. Solo se permiten dígitos, espacios, guiones y el prefijo '+'."
                )
            digits = re.sub(r"\D", "", self.phone_number)
            if not (10 <= len(digits) <= 15):
                raise ValidationError(
                    f"El número de teléfono de la sucursal debe contener entre 10 y 15 dígitos numéricos (actualmente tiene {len(digits)})."
                )

    # ------------------------------------------------------------------------
    # Propiedades alias en español
    # ------------------------------------------------------------------------
    @property
    def nombre(self) -> str:
        return self.name

    @nombre.setter
    def nombre(self, value: str) -> None:
        self.name = value
        self._normalize()
        self.validate()

    @property
    def codigo(self) -> str:
        return self.code

    @codigo.setter
    def codigo(self, value: str) -> None:
        self.code = value
        self._normalize()
        self.validate()

    @property
    def direccion(self) -> Address | None:
        return self.address

    @direccion.setter
    def direccion(self, value: Address | None) -> None:
        self.address = value
        self.validate()

    @property
    def zona_horaria(self) -> str:
        return self.timezone

    @zona_horaria.setter
    def zona_horaria(self, value: str) -> None:
        self.timezone = value
        self._normalize()
        self.validate()

    @property
    def activo(self) -> bool:
        return self.active

    @activo.setter
    def activo(self, value: bool) -> None:
        self.active = value
        self.validate()

    @property
    def correo(self) -> str | None:
        return self.email

    @correo.setter
    def correo(self, value: str | None) -> None:
        self.email = value
        self._normalize()
        self.validate()

    @property
    def telefono(self) -> str | None:
        return self.phone_number

    @telefono.setter
    def telefono(self, value: str | None) -> None:
        self.phone_number = value
        self._normalize()
        self.validate()

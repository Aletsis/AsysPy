"""Entidad Position (Puesto o Cargo laboral)."""

from dataclasses import dataclass

from attendance.domain.common.exceptions import ValidationError


@dataclass
class Position:
    """Entidad que representa un puesto de trabajo o cargo en la organización."""

    name: str
    code: str
    id: int | None = None
    active: bool = True

    def __post_init__(self) -> None:
        self._normalize()
        self.validate()

    def _normalize(self) -> None:
        """Normaliza cadenas de texto antes de la validación."""
        if self.name is not None:
            self.name = str(self.name).strip()

        if self.code is not None:
            self.code = str(self.code).strip().upper()

    def validate(self) -> None:
        """Valida exhaustivamente los atributos e invariantes del puesto."""
        # Validación de ID
        if self.id is not None:
            if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
                raise ValidationError("El ID del puesto debe ser un número entero positivo.")

        # Validación de Nombre
        if not self.name:
            raise ValidationError("El nombre del puesto no puede estar vacío.")
        if len(self.name) > 100:
            raise ValidationError("El nombre del puesto no puede exceder los 100 caracteres.")

        # Validación de Código
        if not self.code:
            raise ValidationError("El código del puesto no puede estar vacío.")
        if any(c.isspace() for c in self.code):
            raise ValidationError("El código del puesto no puede contener espacios en blanco.")
        if len(self.code) > 30:
            raise ValidationError("El código del puesto no puede exceder los 30 caracteres.")

        # Validación de Estado Activo
        if not isinstance(self.active, bool):
            raise ValidationError("El estado activo del puesto debe ser un valor booleano.")

    # ------------------------------------------------------------------------
    # Propiedades alias en español
    # ------------------------------------------------------------------------
    @property
    def codigo(self) -> str:
        return self.code

    @codigo.setter
    def codigo(self, value: str) -> None:
        self.code = value
        self._normalize()
        self.validate()

    @property
    def nombre(self) -> str:
        return self.name

    @nombre.setter
    def nombre(self, value: str) -> None:
        self.name = value
        self._normalize()
        self.validate()

    @property
    def activo(self) -> bool:
        return self.active

    @activo.setter
    def activo(self, value: bool) -> None:
        self.active = value
        self.validate()

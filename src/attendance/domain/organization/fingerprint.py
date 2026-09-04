"""Value Object Fingerprint para plantillas biométricas dactilares."""

from dataclasses import dataclass

from attendance.domain.common.exceptions import ValidationError


@dataclass(frozen=True)
class Fingerprint:
    """Representa una plantilla biométrica de huella dactilar de un colaborador.

    Attributes:
        finger_index: Índice del dedo (0 a 9) según el estándar de relojes biométricos.
        template: Cadena que contiene la plantilla biométrica (base64 o formato del fabricante).
        algorithm_version: Versión del algoritmo biométrico (ej. "10.0", "9.0").
        valid: Indica si la plantilla está activa o es válida.
    """

    finger_index: int
    template: str
    algorithm_version: str = "10.0"
    valid: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.finger_index, int) or isinstance(self.finger_index, bool):
            raise ValidationError("El índice de la huella debe ser un número entero.")
        if not (0 <= self.finger_index <= 9):
            raise ValidationError("El índice de la huella debe estar en el rango de 0 a 9.")
        if not self.template or not str(self.template).strip():
            raise ValidationError("La plantilla biométrica de la huella no puede estar vacía.")
        if not self.algorithm_version or not str(self.algorithm_version).strip():
            raise ValidationError("La versión del algoritmo biométrico no puede estar vacía.")

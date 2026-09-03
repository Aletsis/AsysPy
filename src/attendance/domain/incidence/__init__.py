"""Submódulo de incidencias, permisos y justificaciones."""

from .enums import JustificationStatus, JustificationType
from .justification import Justification

__all__ = [
    "Justification",
    "JustificationType",
    "JustificationStatus",
]

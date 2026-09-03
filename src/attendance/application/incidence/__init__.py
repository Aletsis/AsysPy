"""Submódulo de aplicación para gestión de incidencias, permisos y justificaciones."""

from .register_justification import (
    cancel_justification,
    register_justification,
)

__all__ = [
    "register_justification",
    "cancel_justification",
]

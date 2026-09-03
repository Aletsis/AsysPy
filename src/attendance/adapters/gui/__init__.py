"""Adaptador de Interfaz Gráfica de Escritorio (Desktop GUI) para AsistPy.

Provee una interfaz visual multiplataforma construida sobre PySide6 (Qt for Python)
siguiendo los principios de la Arquitectura Hexagonal y DDD.
"""

__all__ = ["main"]


def main() -> int:
    from attendance.adapters.gui.app import run_app

    return run_app()

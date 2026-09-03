"""Módulo de formateadores para la consola."""

from .colors import blue, bold, cyan, dim, green, red, yellow
from .table import render_table

__all__ = [
    "bold",
    "dim",
    "green",
    "red",
    "yellow",
    "blue",
    "cyan",
    "render_table",
]

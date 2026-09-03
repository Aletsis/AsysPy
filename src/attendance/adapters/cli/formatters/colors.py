"""Utilidades para dar formato con colores ANSI en terminal sin dependencias externas."""

import os
import sys


def _supports_color() -> bool:
    """Detecta si la salida estándar soporta secuencias de escape ANSI."""
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("TERM") == "dumb":
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


class Colors:
    """Códigos de escape ANSI para estilos y colores."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def colorize(text: str, color_code: str) -> str:
    """Aplica un color ANSI al texto solo si el entorno lo soporta."""
    if not _supports_color():
        return text
    return f"{color_code}{text}{Colors.RESET}"


def bold(text: str) -> str:
    return colorize(text, Colors.BOLD)


def dim(text: str) -> str:
    return colorize(text, Colors.DIM)


def green(text: str) -> str:
    return colorize(text, Colors.GREEN)


def red(text: str) -> str:
    return colorize(text, Colors.RED)


def yellow(text: str) -> str:
    return colorize(text, Colors.YELLOW)


def blue(text: str) -> str:
    return colorize(text, Colors.BLUE)


def cyan(text: str) -> str:
    return colorize(text, Colors.CYAN)

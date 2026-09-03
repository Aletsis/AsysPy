"""Punto de ejecución para `python -m attendance.adapters.cli`."""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())

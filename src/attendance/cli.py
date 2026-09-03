"""Módulo de acceso directo a la CLI de AsistPy."""

import sys

from attendance.adapters.cli.main import main

if __name__ == "__main__":
    sys.exit(main())

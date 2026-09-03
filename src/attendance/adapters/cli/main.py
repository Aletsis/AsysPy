"""Punto de entrada principal de la CLI de AsistPy (`asistpy`)."""

import argparse
import sys
from typing import Sequence

from attendance.adapters.cli.commands import (
    register_attendance_subparser,
    register_branch_subparser,
    register_db_subparser,
    register_department_subparser,
    register_device_subparser,
    register_employee_subparser,
    register_report_subparser,
    register_schedule_subparser,
    register_shift_subparser,
)
from attendance.adapters.cli.context import CLIContext, get_common_parser, load_env_file
from attendance.adapters.cli.formatters import red, yellow

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    """Construye el árbol de argumentos y subcomandos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="asistpy",
        description="AsistPy: Herramienta CLI unificada para control de asistencia y relojes biométricos.",
        epilog="Ejecuta 'asistpy <comando> --help' para ver detalles de un comando específico.",
        parents=[get_common_parser()],
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Muestra la versión de AsistPy y finaliza.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando principal a ejecutar")

    # Registrar grupos de comandos
    register_device_subparser(subparsers)
    register_employee_subparser(subparsers)
    register_department_subparser(subparsers)
    register_branch_subparser(subparsers)
    register_shift_subparser(subparsers)
    register_schedule_subparser(subparsers)
    register_attendance_subparser(subparsers)
    register_report_subparser(subparsers)
    register_db_subparser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Función de entrada principal para el comando 'asistpy'."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Cargar variables de entorno desde archivo si aplica
    load_env_file(getattr(args, "env_file", None))

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    ctx = CLIContext(
        backend=getattr(args, "backend", None),
        db_url=getattr(args, "db_url", None),
        verbose=bool(getattr(args, "verbose", False)),
    )

    try:
        return args.func(args, ctx)
    except KeyboardInterrupt:
        print(f"\n{yellow('Operación cancelada por el usuario.')}", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n{red('✘ Error inesperado:')} {e}", file=sys.stderr)
        if ctx.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

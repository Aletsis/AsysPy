"""Comandos de gestión y verificación de base de datos (`asistpy db`)."""

import argparse
import sys

from sqlalchemy import inspect

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table


def _mask_url(url: str | None) -> str:
    """Oculta contraseñas en URLs de conexión para salida segura en consola."""
    if not url:
        return "N/A"
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        user_pass, host_db = rest.split("@", 1)
        if ":" in user_pass:
            user = user_pass.split(":", 1)[0]
            return f"{scheme}://{user}:***@{host_db}"
    return url


def cmd_db_init(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Inicializa las tablas y el esquema de la base de datos."""
    print(f"{cyan(bold('Iniciando esquema de base de datos...'))}")
    try:
        bundle = ctx.get_bundle(init_tables=True)
        if bundle.database is not None:
            inspector = inspect(bundle.database.engine)
            tables = inspector.get_table_names()
            print(f"{green('✔')} Tablas creadas/verificadas exitosamente en la base de datos:")
            for t in sorted(tables):
                print(f"  • {bold(t)}")
            print(f"\n{bold('Total de tablas:')} {len(tables)}")
        else:
            print(f"{green('✔')} Repositorios inicializados en memoria (no persistentes).")
        return 0
    except Exception as e:
        print(f"{red('✘ Error al inicializar base de datos:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def cmd_db_status(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Verifica la conectividad y muestra el conteo de registros en la base de datos."""
    print(f"{cyan(bold('Comprobando estado de la base de datos...'))}")
    try:
        bundle = ctx.get_bundle(init_tables=False)

        backend = (ctx.backend or "sqlite").lower()
        db_url = _mask_url(ctx.db_url or (bundle.database.url if bundle.database else "In-Memory"))

        # Obtener conteos básicos de entidades
        devices_count = len(bundle.device_repo.list_all())
        employees_count = len(bundle.employee_repo.list_all()) if hasattr(bundle.employee_repo, "list_all") else 0
        logs_count = len(bundle.attendance_repo.list_all()) if hasattr(bundle.attendance_repo, "list_all") else 0
        daily_count = len(bundle.daily_attendance_repo.list_all()) if hasattr(bundle.daily_attendance_repo, "list_all") else 0

        info_rows = [
            ["Motor / Backend", backend],
            ["URL de Conexión", db_url],
            ["Estado de Conexión", green("Conectado (OK)")],
            ["Dispositivos en Catálogo", str(devices_count)],
            ["Empleados Registrados", str(employees_count)],
            ["Marcaciones Crudas", str(logs_count)],
            ["Jornadas Evaluadas", str(daily_count)],
        ]

        table = render_table(
            headers=["Parámetro", "Valor"],
            rows=info_rows,
            alignments=["left", "left"],
        )
        print(table)
        return 0
    except Exception as e:
        print(f"{red('✘ Error al conectar con la base de datos:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def register_db_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy db`."""
    db_parser = subparsers.add_parser(
        "db",
        help="Gestión y diagnóstico de la base de datos",
        description="Inicializa tablas y comprueba conectividad con la base de datos configurada.",
    )
    db_subparsers = db_parser.add_subparsers(dest="db_action", required=True)

    # asistpy db init
    init_parser = db_subparsers.add_parser(
        "init",
        parents=[get_common_parser()],
        help="Crea las tablas y esquemas necesarios",
        description="Crea todas las tablas requeridas según el backend de base de datos activo.",
    )
    init_parser.set_defaults(func=cmd_db_init)

    # asistpy db status
    status_parser = db_subparsers.add_parser(
        "status",
        parents=[get_common_parser()],
        help="Muestra el estado de la conexión y conteo de entidades",
        description="Verifica la conexión a la base de datos y muestra un resumen del inventario de datos.",
    )
    status_parser.set_defaults(func=cmd_db_status)

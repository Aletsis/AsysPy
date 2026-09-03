"""Comandos de administración y catálogo de turnos laborales (`asistpy shift`)."""

import argparse
import sys
from datetime import time

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.schedule.enums import ShiftCategory
from attendance.domain.schedule.shift import ShiftDefinition


def _parse_time(time_str: str) -> time:
    """Convierte una cadena HH:MM o HH:MM:SS a time."""
    try:
        parts = [int(p) for p in time_str.split(":")]
        if len(parts) == 2:
            return time(parts[0], parts[1], 0)
        elif len(parts) == 3:
            return time(parts[0], parts[1], parts[2])
    except Exception:
        pass
    raise argparse.ArgumentTypeError(f"Formato de hora inválido: '{time_str}'. Use HH:MM o HH:MM:SS.")


def cmd_shift_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo turno laboral en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)

    start = _parse_time(args.start_time)
    end = _parse_time(args.end_time)
    try:
        category = ShiftCategory(args.category.lower()) if args.category else ShiftCategory.PERSONALIZADO
    except ValueError:
        print(
            f"{red('✘ Error:')} Categoría '{args.category}' no es válida. Opciones: {', '.join(c.value for c in ShiftCategory)}.",
            file=sys.stderr,
        )
        return 1

    shift = ShiftDefinition(
        id=None,
        name=args.name,
        start_time=start,
        end_time=end,
        tolerance_minutes=args.tolerance or 0,
        crosses_midnight=args.crosses_midnight,
        category=category,
    )

    saved = bundle.shift_repo.save(shift)
    print(f"\n{green('✔')} Turno {bold(saved.name)} registrado exitosamente con ID {saved.id}.")
    headers = ["ID", "Nombre", "Categoría", "Entrada", "Salida", "Tolerancia", "Cruza Medianoche"]
    rows = [[
        str(saved.id or "-"),
        saved.name,
        saved.category.value,
        saved.start_time.strftime("%H:%M") if saved.start_time else "--:--",
        saved.end_time.strftime("%H:%M") if saved.end_time else "--:--",
        f"{saved.tolerance_minutes} min",
        "Sí" if saved.crosses_midnight else "No",
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "center", "center", "right", "center"]))
    return 0


def cmd_shift_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un turno laboral."""
    bundle = ctx.get_bundle(init_tables=False)
    shift = bundle.shift_repo.get_by_id(args.shift_id)
    if not shift:
        print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
        return 1

    rows = [
        ["ID", str(shift.id or "-")],
        ["Nombre del Turno", shift.name],
        ["Categoría", shift.category.value],
        ["Hora de Entrada", shift.start_time.strftime("%H:%M:%S") if shift.start_time else "--:--:--"],
        ["Hora de Salida", shift.end_time.strftime("%H:%M:%S") if shift.end_time else "--:--:--"],
        ["Tolerancia de Retardo", f"{shift.tolerance_minutes} minutos"],
        ["Cruza Medianoche", "Sí" if shift.crosses_midnight else "No"],
        ["Turno Partido / Segmentos", str(len(shift.segments)) if shift.segments else "No (Turno Regular)"],
    ]
    print(f"\n{cyan(bold('Detalle de Turno Laboral:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_shift_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista todos los turnos registrados en el catálogo."""
    bundle = ctx.get_bundle(init_tables=False)
    shifts = bundle.shift_repo.list_all()

    if not shifts:
        print(f"{yellow('No se encontraron turnos registrados en el catálogo.')}")
        return 0

    headers = ["ID", "Nombre", "Categoría", "Entrada", "Salida", "Tolerancia", "Cruza Medianoche"]
    rows = []
    for s in shifts:
        rows.append([
            str(s.id or "-"),
            s.name,
            s.category.value,
            s.start_time.strftime("%H:%M") if s.start_time else "--:--",
            s.end_time.strftime("%H:%M") if s.end_time else "--:--",
            f"{s.tolerance_minutes} min",
            "Sí" if s.crosses_midnight else "No",
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "center", "center", "right", "center"],
    )
    print(table)
    print(f"\n{bold('Total turnos:')} {len(shifts)}")
    return 0


def cmd_shift_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica los datos de un turno laboral existente."""
    bundle = ctx.get_bundle(init_tables=True)
    shift = bundle.shift_repo.get_by_id(args.shift_id)
    if not shift:
        print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
        return 1

    if args.name is not None:
        shift.name = args.name
    if args.start_time is not None:
        shift.start_time = _parse_time(args.start_time)
    if args.end_time is not None:
        shift.end_time = _parse_time(args.end_time)
    if args.tolerance is not None:
        shift.tolerance_minutes = args.tolerance
    if args.category is not None:
        try:
            shift.category = ShiftCategory(args.category.lower())
        except ValueError:
            print(
                f"{red('✘ Error:')} Categoría '{args.category}' no es válida. Opciones: {', '.join(c.value for c in ShiftCategory)}.",
                file=sys.stderr,
            )
            return 1
    if args.crosses_midnight:
        shift.crosses_midnight = True
    elif args.no_crosses_midnight:
        shift.crosses_midnight = False

    saved = bundle.shift_repo.save(shift)
    print(f"\n{green('✔')} Turno {bold(saved.name)} (ID: {saved.id}) actualizado exitosamente.")
    return 0


def cmd_shift_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un turno del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    shift = bundle.shift_repo.get_by_id(args.shift_id)
    if not shift or shift.id is None:
        print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
        return 1

    success = bundle.shift_repo.delete(shift.id)
    if success:
        print(f"\n{green('✔')} Turno '{bold(shift.name)}' (ID: {shift.id}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el turno con ID {shift.id}.", file=sys.stderr)
        return 1


def register_shift_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy shift`."""
    shift_parser = subparsers.add_parser(
        "shift",
        help="Gestión y catálogo CRUD de turnos de trabajo",
        description="Permite definir horarios, tolerancias, categorías y turnos nocturnos.",
    )
    shift_subparsers = shift_parser.add_subparsers(dest="shift_action", required=True)

    # asistpy shift add
    add_parser = shift_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra un nuevo turno de trabajo",
    )
    add_parser.add_argument("--name", required=True, help="Nombre del turno (ej. 'Matutino 8-16')")
    add_parser.add_argument("--start-time", required=True, help="Hora de entrada HH:MM o HH:MM:SS")
    add_parser.add_argument("--end-time", required=True, help="Hora de salida HH:MM o HH:MM:SS")
    add_parser.add_argument("--tolerance", type=int, default=0, help="Minutos de tolerancia para retardo")
    add_parser.add_argument("--crosses-midnight", action="store_true", help="El turno cruza medianoche (ej. nocturno 22 a 06)")
    add_parser.add_argument(
        "--category",
        choices=[c.value for c in ShiftCategory],
        default="personalizado",
        help=f"Categoría del turno ({', '.join(c.value for c in ShiftCategory)})",
    )
    add_parser.set_defaults(func=cmd_shift_add)

    # asistpy shift show
    show_parser = shift_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un turno",
    )
    show_parser.add_argument("--shift-id", type=int, required=True, help="ID del turno a consultar")
    show_parser.set_defaults(func=cmd_shift_show)

    # asistpy shift edit
    edit_parser = shift_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los parámetros de un turno existente",
    )
    edit_parser.add_argument("--shift-id", type=int, required=True, help="ID del turno a modificar")
    edit_parser.add_argument("--name", help="Nuevo nombre del turno")
    edit_parser.add_argument("--start-time", help="Nueva hora de entrada HH:MM")
    edit_parser.add_argument("--end-time", help="Nueva hora de salida HH:MM")
    edit_parser.add_argument("--tolerance", type=int, help="Nuevos minutos de tolerancia")
    edit_parser.add_argument(
        "--category",
        choices=[c.value for c in ShiftCategory],
        help=f"Nueva categoría ({', '.join(c.value for c in ShiftCategory)})",
    )
    midnight_group = edit_parser.add_mutually_exclusive_group()
    midnight_group.add_argument("--crosses-midnight", action="store_true", help="Marcar que cruza medianoche")
    midnight_group.add_argument("--no-crosses-midnight", action="store_true", help="Marcar que no cruza medianoche")
    edit_parser.set_defaults(func=cmd_shift_edit)

    # asistpy shift delete
    del_parser = shift_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina un turno del catálogo",
    )
    del_parser.add_argument("--shift-id", type=int, required=True, help="ID del turno a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_shift_delete)

    # asistpy shift list
    list_parser = shift_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los turnos registrados",
    )
    list_parser.set_defaults(func=cmd_shift_list)

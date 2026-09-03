"""Comandos de asignación y catálogo de horarios (`asistpy schedule`)."""

import argparse
import sys
from datetime import date

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode


def _parse_date(date_str: str) -> date:
    """Convierte una cadena YYYY-MM-DD a date."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido: '{date_str}'. Use YYYY-MM-DD.")


def cmd_schedule_assign(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Asigna un turno u horario a un empleado."""
    bundle = ctx.get_bundle(init_tables=True)

    emp = bundle.employee_repo.get_by_pin(args.employee_pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.employee_pin}' no encontrado.", file=sys.stderr)
        return 1

    shift = bundle.shift_repo.get_by_id(args.shift_id)
    if not shift:
        print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado en catálogo.", file=sys.stderr)
        return 1

    valid_from = _parse_date(args.valid_from) if args.valid_from else date.today()
    valid_until = _parse_date(args.valid_until) if args.valid_until else None
    mode = AssignmentMode(args.mode.lower()) if args.mode else AssignmentMode.FIXED

    assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin=args.employee_pin,
        mode=mode,
        valid_from=valid_from,
        valid_until=valid_until,
        shift_definition_id=shift.id,
    )

    saved = bundle.schedule_assignment_repo.save(assignment)
    print(f"\n{green('✔')} Horario asignado exitosamente con ID {bold(str(saved.id))}.")
    headers = ["ID", "PIN Empleado", "Empleado", "Turno", "Modo", "Válido Desde", "Válido Hasta"]
    rows = [[
        str(saved.id or "-"),
        saved.employee_pin,
        emp.full_name,
        shift.name,
        saved.mode.value,
        saved.valid_from.isoformat(),
        saved.valid_until.isoformat() if saved.valid_until else "Indefinido",
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "left", "center", "center", "center"]))
    return 0


def cmd_schedule_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de una asignación de horario."""
    bundle = ctx.get_bundle(init_tables=False)
    assignment = bundle.schedule_assignment_repo.get_by_id(args.assignment_id)
    if not assignment:
        print(f"{red('✘ Error:')} Asignación con ID {args.assignment_id} no encontrada.", file=sys.stderr)
        return 1

    emp = bundle.employee_repo.get_by_pin(assignment.employee_pin)
    emp_name = emp.full_name if emp else "-"
    shift_name = "-"
    if assignment.shift_definition_id:
        shift = bundle.shift_repo.get_by_id(assignment.shift_definition_id)
        if shift:
            shift_name = shift.name

    rows = [
        ["ID Asignación", str(assignment.id or "-")],
        ["PIN Empleado", assignment.employee_pin],
        ["Nombre Empleado", emp_name],
        ["Modo de Asignación", assignment.mode.value],
        ["Turno Asignado ID", str(assignment.shift_definition_id or "-")],
        ["Nombre del Turno", shift_name],
        ["Válido Desde", assignment.valid_from.isoformat()],
        ["Válido Hasta", assignment.valid_until.isoformat() if assignment.valid_until else "Vigente / Indefinido"],
    ]
    print(f"\n{cyan(bold('Detalle de Asignación de Horario:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_schedule_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista las asignaciones de horarios registradas."""
    bundle = ctx.get_bundle(init_tables=False)
    assignments = bundle.schedule_assignment_repo.list_all(employee_pin=args.employee_pin)

    if not assignments:
        print(f"{yellow('No se encontraron asignaciones de horario registradas.')}")
        return 0

    headers = ["ID", "PIN Empleado", "Modo", "Turno ID", "Válido Desde", "Válido Hasta"]
    rows = []
    for a in assignments:
        rows.append([
            str(a.id or "-"),
            a.employee_pin,
            a.mode.value,
            str(a.shift_definition_id or "-"),
            a.valid_from.isoformat(),
            a.valid_until.isoformat() if a.valid_until else "Indefinido",
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "center", "right", "center", "center"],
    )
    print(table)
    print(f"\n{bold('Total asignaciones:')} {len(assignments)}")
    return 0


def cmd_schedule_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica los datos de una asignación de horario existente."""
    bundle = ctx.get_bundle(init_tables=True)
    assignment = bundle.schedule_assignment_repo.get_by_id(args.assignment_id)
    if not assignment:
        print(f"{red('✘ Error:')} Asignación con ID {args.assignment_id} no encontrada.", file=sys.stderr)
        return 1

    if args.shift_id is not None:
        shift = bundle.shift_repo.get_by_id(args.shift_id)
        if not shift:
            print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
            return 1
        assignment.shift_definition_id = args.shift_id

    if args.valid_until is not None:
        assignment.valid_until = _parse_date(args.valid_until)
    if args.valid_from is not None:
        assignment.valid_from = _parse_date(args.valid_from)
    if args.mode is not None:
        assignment.mode = AssignmentMode(args.mode.lower())

    saved = bundle.schedule_assignment_repo.save(assignment)
    print(f"\n{green('✔')} Asignación de horario {bold(str(saved.id))} actualizada exitosamente.")
    return 0


def cmd_schedule_close(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Cierra la vigencia de una asignación de horario."""
    bundle = ctx.get_bundle(init_tables=True)
    assignment = bundle.schedule_assignment_repo.get_by_id(args.assignment_id)
    if not assignment:
        print(f"{red('✘ Error:')} Asignación con ID {args.assignment_id} no encontrada.", file=sys.stderr)
        return 1

    until = _parse_date(args.valid_until) if args.valid_until else date.today()
    bundle.schedule_assignment_repo.close_assignment(args.assignment_id, until)
    print(f"\n{green('✔')} Asignación {bold(str(args.assignment_id))} cerrada con vigencia hasta {bold(until.isoformat())}.")
    return 0


def cmd_schedule_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina una asignación de horario."""
    bundle = ctx.get_bundle(init_tables=True)
    assignment = bundle.schedule_assignment_repo.get_by_id(args.assignment_id)
    if not assignment:
        print(f"{red('✘ Error:')} Asignación con ID {args.assignment_id} no encontrada.", file=sys.stderr)
        return 1

    success = bundle.schedule_assignment_repo.delete(args.assignment_id)
    if success:
        print(f"\n{green('✔')} Asignación de horario con ID {args.assignment_id} eliminada correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar la asignación con ID {args.assignment_id}.", file=sys.stderr)
        return 1


def register_schedule_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy schedule`."""
    sched_parser = subparsers.add_parser(
        "schedule",
        help="Gestión y asignación CRUD de horarios y turnos a empleados",
        description="Permite asignar turnos a empleados, definir vigencias, cerrar asignaciones y consultar horarios.",
    )
    sched_subparsers = sched_parser.add_subparsers(dest="schedule_action", required=True)

    # asistpy schedule assign (alias: add)
    assign_parser = sched_subparsers.add_parser(
        "assign",
        parents=[get_common_parser()],
        help="Asigna un turno laboral a un empleado",
    )
    assign_parser.add_argument("--employee-pin", required=True, help="PIN del empleado (ej. 'E100')")
    assign_parser.add_argument("--shift-id", type=int, required=True, help="ID del turno a asignar")
    assign_parser.add_argument("--mode", choices=["fixed", "rotating", "open"], default="fixed", help="Modo de horario")
    assign_parser.add_argument("--valid-from", help="Fecha de inicio YYYY-MM-DD (predeterminada: hoy)")
    assign_parser.add_argument("--valid-until", help="Fecha límite de vigencia YYYY-MM-DD (opcional)")
    assign_parser.set_defaults(func=cmd_schedule_assign)

    # asistpy schedule show
    show_parser = sched_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle de una asignación de horario",
    )
    show_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación")
    show_parser.set_defaults(func=cmd_schedule_show)

    # asistpy schedule edit
    edit_parser = sched_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los parámetros de una asignación de horario",
    )
    edit_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a modificar")
    edit_parser.add_argument("--shift-id", type=int, help="Nuevo ID de turno asignado")
    edit_parser.add_argument("--mode", choices=["fixed", "rotating", "open"], help="Nuevo modo de horario")
    edit_parser.add_argument("--valid-from", help="Nueva fecha de inicio YYYY-MM-DD")
    edit_parser.add_argument("--valid-until", help="Nueva fecha de término YYYY-MM-DD")
    edit_parser.set_defaults(func=cmd_schedule_edit)

    # asistpy schedule close
    close_parser = sched_subparsers.add_parser(
        "close",
        parents=[get_common_parser()],
        help="Cierra la vigencia de una asignación de horario",
    )
    close_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a cerrar")
    close_parser.add_argument("--valid-until", help="Fecha de cierre YYYY-MM-DD (predeterminada: hoy)")
    close_parser.set_defaults(func=cmd_schedule_close)

    # asistpy schedule delete
    del_parser = sched_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina una asignación de horario",
    )
    del_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_schedule_delete)

    # asistpy schedule list
    list_parser = sched_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista las asignaciones de horario",
    )
    list_parser.add_argument("--employee-pin", help="Filtrar por PIN del empleado")
    list_parser.set_defaults(func=cmd_schedule_list)

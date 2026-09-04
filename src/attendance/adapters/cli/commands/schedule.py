"""Comandos de asignación y catálogo de horarios (`asistpy schedule`)."""

import argparse
import sys
from datetime import date
from typing import Any

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.application.schedule.plan_builder import (
    RestModeOption,
    SchedulePlanBuilder,
    SchedulePlanConfig,
    ShiftModeOption,
)
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, RotationFrequency, Weekday
from attendance.domain.schedule.exception import ScheduleException
from attendance.domain.schedule.rotation import RotationPattern
from attendance.domain.schedule.shift import ShiftDefinition


def _parse_date(date_str: str) -> date:
    """Convierte una cadena YYYY-MM-DD a date."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Formato de fecha inválido: '{date_str}'. Use YYYY-MM-DD."
        )


DAY_NAME_MAP: dict[str, Weekday] = {
    "lunes": Weekday.MONDAY,
    "lun": Weekday.MONDAY,
    "monday": Weekday.MONDAY,
    "mon": Weekday.MONDAY,
    "0": Weekday.MONDAY,
    "martes": Weekday.TUESDAY,
    "mar": Weekday.TUESDAY,
    "tuesday": Weekday.TUESDAY,
    "tue": Weekday.TUESDAY,
    "1": Weekday.TUESDAY,
    "miercoles": Weekday.WEDNESDAY,
    "miércoles": Weekday.WEDNESDAY,
    "mie": Weekday.WEDNESDAY,
    "mié": Weekday.WEDNESDAY,
    "wednesday": Weekday.WEDNESDAY,
    "wed": Weekday.WEDNESDAY,
    "2": Weekday.WEDNESDAY,
    "jueves": Weekday.THURSDAY,
    "jue": Weekday.THURSDAY,
    "thursday": Weekday.THURSDAY,
    "thu": Weekday.THURSDAY,
    "3": Weekday.THURSDAY,
    "viernes": Weekday.FRIDAY,
    "vie": Weekday.FRIDAY,
    "friday": Weekday.FRIDAY,
    "fri": Weekday.FRIDAY,
    "4": Weekday.FRIDAY,
    "sabado": Weekday.SATURDAY,
    "sábado": Weekday.SATURDAY,
    "sab": Weekday.SATURDAY,
    "sáb": Weekday.SATURDAY,
    "saturday": Weekday.SATURDAY,
    "sat": Weekday.SATURDAY,
    "5": Weekday.SATURDAY,
    "domingo": Weekday.SUNDAY,
    "dom": Weekday.SUNDAY,
    "sunday": Weekday.SUNDAY,
    "sun": Weekday.SUNDAY,
    "6": Weekday.SUNDAY,
}

WEEKDAY_SPANISH: dict[Weekday, str] = {
    Weekday.MONDAY: "Lun",
    Weekday.TUESDAY: "Mar",
    Weekday.WEDNESDAY: "Mié",
    Weekday.THURSDAY: "Jue",
    Weekday.FRIDAY: "Vie",
    Weekday.SATURDAY: "Sáb",
    Weekday.SUNDAY: "Dom",
}


def _parse_days_list(days_str: str) -> set[Weekday]:
    """Convierte una cadena separada por comas (ej. 'lun,mar,vie' o 'sunday') en un conjunto de Weekday."""
    parts = [p.strip().lower() for p in days_str.split(",") if p.strip()]
    result: set[Weekday] = set()
    for p in parts:
        if p not in DAY_NAME_MAP:
            raise argparse.ArgumentTypeError(
                f"Día de la semana no reconocido: '{p}'. Use nombres en español o inglés (ej. domingo, lun, mon)."
            )
        result.add(DAY_NAME_MAP[p])
    return result


def _format_weekdays_and_rest(working_weekdays: set[Weekday] | None) -> str:
    """Devuelve una descripción legible de los días de descanso y laborables."""
    if working_weekdays is None:
        return "Todos (L-D)"
    all_days = {Weekday(i) for i in range(7)}
    if working_weekdays == all_days:
        return "Todos (L-D)"
    rest_days = all_days - working_weekdays
    if not rest_days:
        return "Todos (L-D)"
    rest_str = ", ".join(WEEKDAY_SPANISH[d] for d in sorted(rest_days, key=lambda x: x.value))
    return f"Descanso: {rest_str}"


# ============================================================================
# 1. Asignaciones de Horarios (asistpy schedule assign/list/show/edit/close/delete)
# ============================================================================


def cmd_schedule_assign(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Asigna un turno u horario a un empleado."""
    bundle = ctx.get_bundle(init_tables=True)

    emp = bundle.employee_repo.get_by_pin(args.employee_pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.employee_pin}' no encontrado.", file=sys.stderr)
        return 1

    mode = AssignmentMode(args.mode.lower()) if args.mode else AssignmentMode.FIXED
    shift = None
    rotation_pattern = None

    if mode == AssignmentMode.FIXED:
        if args.shift_id is None:
            print(f"{red('✘ Error:')} Para modo fijo ('fixed') debe especificar --shift-id.", file=sys.stderr)
            return 1
        shift = bundle.shift_repo.get_by_id(args.shift_id)
        if not shift:
            print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado en catálogo.", file=sys.stderr)
            return 1
    elif mode == AssignmentMode.ROTATING:
        if args.rotation_pattern_id is None:
            print(f"{red('✘ Error:')} Para modo rotativo ('rotating') debe especificar --rotation-pattern-id.", file=sys.stderr)
            return 1
        rotation_pattern = bundle.rotation_pattern_repo.get_by_id(args.rotation_pattern_id)
        if not rotation_pattern:
            print(f"{red('✘ Error:')} Patrón de rotación con ID {args.rotation_pattern_id} no encontrado.", file=sys.stderr)
            return 1
        if args.shift_id is not None:
            shift = bundle.shift_repo.get_by_id(args.shift_id)

    # Determinar días laborables y de descanso
    working_weekdays: set[Weekday] | None = None
    if getattr(args, "rest_days", None):
        rest_set = _parse_days_list(args.rest_days)
        working_weekdays = {Weekday(i) for i in range(7)} - rest_set
    elif getattr(args, "working_days", None):
        working_weekdays = _parse_days_list(args.working_days)

    valid_from = _parse_date(args.valid_from) if args.valid_from else date.today()
    valid_until = _parse_date(args.valid_until) if args.valid_until else None

    assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin=args.employee_pin,
        mode=mode,
        valid_from=valid_from,
        valid_until=valid_until,
        working_weekdays=working_weekdays,
        shift_definition_id=shift.id if shift else None,
        rotation_pattern_id=rotation_pattern.id if rotation_pattern else None,
    )

    saved = bundle.schedule_assignment_repo.save(assignment)
    print(f"\n{green('✔')} Horario asignado exitosamente con ID {bold(str(saved.id))}.")

    desc_detail = (
        shift.name if shift else (f"Patrón: {rotation_pattern.name}" if rotation_pattern else "-")
    )
    rest_detail = _format_weekdays_and_rest(saved.working_weekdays)

    headers = ["ID", "PIN", "Empleado", "Horario / Turno", "Modo", "Descanso / Días", "Desde", "Hasta"]
    rows = [[
        str(saved.id or "-"),
        saved.employee_pin,
        emp.full_name,
        desc_detail,
        saved.mode.value.upper(),
        rest_detail,
        saved.valid_from.isoformat(),
        saved.valid_until.isoformat() if saved.valid_until else "Indefinido",
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "left", "center", "left", "center", "center"]))
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

    pattern_name = "-"
    if assignment.rotation_pattern_id:
        pattern = bundle.rotation_pattern_repo.get_by_id(assignment.rotation_pattern_id)
        if pattern:
            pattern_name = f"{pattern.name} (ID {pattern.id})"

    rows = [
        ["ID Asignación", str(assignment.id or "-")],
        ["PIN Empleado", assignment.employee_pin],
        ["Nombre Empleado", emp_name],
        ["Modo de Asignación", assignment.mode.value.upper()],
        ["Turno Fijo", shift_name],
        ["Patrón de Rotación", pattern_name],
        ["Esquema de Descanso", _format_weekdays_and_rest(assignment.working_weekdays)],
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

    shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all() if s.id is not None}
    patterns_map = {p.id: p.name for p in bundle.rotation_pattern_repo.list_all() if p.id is not None}

    headers = ["ID", "PIN", "Modo", "Turno / Patrón", "Esquema Descanso", "Desde", "Hasta"]
    rows = []
    for a in assignments:
        if a.mode == AssignmentMode.FIXED:
            detail = shifts_map.get(a.shift_definition_id, f"Turno #{a.shift_definition_id}") if a.shift_definition_id is not None else "-"
        elif a.mode == AssignmentMode.ROTATING:
            detail = patterns_map.get(a.rotation_pattern_id, f"Patrón #{a.rotation_pattern_id}") if a.rotation_pattern_id is not None else "-"
        else:
            detail = "Horario Flexible"

        rows.append([
            str(a.id or "-"),
            a.employee_pin,
            a.mode.value.upper(),
            detail,
            _format_weekdays_and_rest(a.working_weekdays),
            a.valid_from.isoformat(),
            a.valid_until.isoformat() if a.valid_until else "Indefinido",
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "center", "left", "left", "center", "center"],
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

    if getattr(args, "shift_id", None) is not None:
        shift = bundle.shift_repo.get_by_id(args.shift_id)
        if not shift:
            print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
            return 1
        assignment.shift_definition_id = args.shift_id

    if getattr(args, "rotation_pattern_id", None) is not None:
        pattern = bundle.rotation_pattern_repo.get_by_id(args.rotation_pattern_id)
        if not pattern:
            print(f"{red('✘ Error:')} Patrón con ID {args.rotation_pattern_id} no encontrado.", file=sys.stderr)
            return 1
        assignment.rotation_pattern_id = args.rotation_pattern_id

    if getattr(args, "rest_days", None):
        rest_set = _parse_days_list(args.rest_days)
        assignment.working_weekdays = {Weekday(i) for i in range(7)} - rest_set
    elif getattr(args, "working_days", None):
        assignment.working_weekdays = _parse_days_list(args.working_days)

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


# ============================================================================
# 2. Patrones de Rotación (asistpy schedule rotation add/list/show/delete)
# ============================================================================


def _parse_rotation_sequence(seq_str: str) -> list[int | None]:
    """Convierte una cadena como '1,1,1,1,1,1,OFF' en una lista de IDs de turno y None."""
    items = [s.strip().upper() for s in seq_str.split(",") if s.strip()]
    seq: list[int | None] = []
    for item in items:
        if item in ("OFF", "REST", "NONE", "DESCANSO", "LIBRE", "-"):
            seq.append(None)
        else:
            try:
                seq.append(int(item))
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"Elemento de secuencia inválido: '{item}'. Use ID numérico de turno o 'OFF'/'REST' para descanso."
                )
    return seq


def cmd_schedule_rotation_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo patrón de rotación cíclico (ej. 6x1, 5x2, 24x48)."""
    bundle = ctx.get_bundle(init_tables=True)

    try:
        sequence = _parse_rotation_sequence(args.sequence)
    except Exception as e:
        print(f"{red('✘ Error:')} {e}", file=sys.stderr)
        return 1

    if not sequence:
        print(f"{red('✘ Error:')} La secuencia de rotación no puede estar vacía.", file=sys.stderr)
        return 1

    try:
        freq = RotationFrequency(args.frequency.lower()) if args.frequency else RotationFrequency.DAILY
    except ValueError:
        print(f"{red('✘ Error:')} Frecuencia no soportada. Use daily, weekly, biweekly, monthly.", file=sys.stderr)
        return 1

    anchor = _parse_date(args.anchor_date) if args.anchor_date else date.today()

    pattern = RotationPattern(
        id=None,
        name=args.name,
        shift_sequence=sequence,
        frequency=freq,
        anchor_date=anchor,
    )

    saved = bundle.rotation_pattern_repo.save(pattern)
    print(f"\n{green('✔')} Patrón de rotación {bold(saved.name)} registrado con ID {bold(str(saved.id))}.")

    seq_repr = " → ".join("Descanso" if s is None else f"Turno #{s}" for s in saved.shift_sequence)
    print(f"  • Secuencia cíclica ({len(saved.shift_sequence)} períodos): {seq_repr}")
    print(f"  • Frecuencia: {saved.frequency.value}")
    print(f"  • Fecha ancla: {saved.anchor_date}")
    return 0


def cmd_schedule_rotation_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista los patrones de rotación disponibles en el catálogo."""
    bundle = ctx.get_bundle(init_tables=False)
    patterns = bundle.rotation_pattern_repo.list_all()

    if not patterns:
        print(f"{yellow('No se encontraron patrones de rotación registrados.')}")
        return 0

    headers = ["ID", "Nombre", "Períodos", "Secuencia Resumida", "Frecuencia", "Fecha Ancla"]
    rows = []
    for p in patterns:
        work_count = sum(1 for s in p.shift_sequence if s is not None)
        rest_count = sum(1 for s in p.shift_sequence if s is None)
        summary = f"{work_count} Trab. / {rest_count} Desc."
        rows.append([
            str(p.id or "-"),
            p.name,
            str(len(p.shift_sequence)),
            summary,
            p.frequency.value,
            p.anchor_date.isoformat(),
        ])

    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "center", "left", "center", "center"]))
    print(f"\n{bold('Total patrones:')} {len(patterns)}")
    return 0


def cmd_schedule_rotation_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un patrón de rotación."""
    bundle = ctx.get_bundle(init_tables=False)
    p = bundle.rotation_pattern_repo.get_by_id(args.pattern_id)
    if not p:
        print(f"{red('✘ Error:')} Patrón con ID {args.pattern_id} no encontrado.", file=sys.stderr)
        return 1

    shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all() if s.id is not None}
    seq_steps = []
    for idx, s_id in enumerate(p.shift_sequence, start=1):
        if s_id is None:
            seq_steps.append(f"Paso {idx}: [DESCANSO]")
        else:
            s_name = shifts_map.get(s_id, f"Turno #{s_id}")
            seq_steps.append(f"Paso {idx}: {s_name} (ID {s_id})")

    rows = [
        ["ID Patrón", str(p.id or "-")],
        ["Nombre", p.name],
        ["Frecuencia", p.frequency.value],
        ["Fecha Ancla", p.anchor_date.isoformat()],
        ["Duración del Ciclo", f"{len(p.shift_sequence)} períodos"],
        ["Secuencia Detallada", "\n".join(seq_steps)],
    ]
    print(f"\n{cyan(bold('Detalle de Patrón de Rotación:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_schedule_rotation_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un patrón de rotación."""
    bundle = ctx.get_bundle(init_tables=True)
    p = bundle.rotation_pattern_repo.get_by_id(args.pattern_id)
    if not p:
        print(f"{red('✘ Error:')} Patrón con ID {args.pattern_id} no encontrado.", file=sys.stderr)
        return 1

    success = bundle.rotation_pattern_repo.delete(args.pattern_id)
    if success:
        print(f"\n{green('✔')} Patrón '{p.name}' (ID {args.pattern_id}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el patrón con ID {args.pattern_id}.", file=sys.stderr)
        return 1


# ============================================================================
# 3. Excepciones y Eventualidades (asistpy schedule exception add/list/delete)
# ============================================================================


def cmd_schedule_exception_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra una excepción/eventualidad puntual de horario (forzar descanso o turno extraordinario)."""
    bundle = ctx.get_bundle(init_tables=True)

    emp = bundle.employee_repo.get_by_pin(args.employee_pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.employee_pin}' no encontrado.", file=sys.stderr)
        return 1

    target_date = _parse_date(args.date)

    if not args.rest_day and args.shift_id is None:
        print(f"{red('✘ Error:')} Debe especificar --rest-day (para forzar descanso) o --shift-id (para turno específico).", file=sys.stderr)
        return 1

    shift = None
    shift_id = None
    if not args.rest_day and args.shift_id is not None:
        shift = bundle.shift_repo.get_by_id(args.shift_id)
        if not shift:
            print(f"{red('✘ Error:')} Turno con ID {args.shift_id} no encontrado.", file=sys.stderr)
            return 1
        shift_id = shift.id

    exception = ScheduleException(
        id=None,
        employee_pin=args.employee_pin,
        date=target_date,
        shift_definition_id=shift_id,
        reason=args.reason or "Eventualidad de horario",
    )

    if not bundle.schedule_exception_repo:
        print(f"{red('✘ Error:')} Repositorio de excepciones de horario no disponible.", file=sys.stderr)
        return 1

    saved = bundle.schedule_exception_repo.save(exception)
    shift_desc = shift.name if shift else (f"Turno #{saved.shift_definition_id}" if saved.shift_definition_id else "Turno")
    tipo = yellow("DESCANSO FORZADO (OFF)") if saved.shift_definition_id is None else green(f"TURNO FORZADO: {shift_desc}")
    print(f"\n{green('✔')} Eventualidad de horario registrada exitosamente con ID {bold(str(saved.id))}.")
    print(f"  • Colaborador: {bold(emp.full_name)} ({saved.employee_pin})")
    print(f"  • Fecha: {bold(saved.date.isoformat())}")
    print(f"  • Efecto: {tipo}")
    print(f"  • Motivo: {saved.reason}")
    return 0


def cmd_schedule_exception_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista las excepciones y eventualidades de horario registradas."""
    bundle = ctx.get_bundle(init_tables=False)
    if not bundle.schedule_exception_repo:
        print(f"{red('✘ Error:')} Repositorio de excepciones no disponible.", file=sys.stderr)
        return 1

    if args.employee_pin:
        exceptions = bundle.schedule_exception_repo.list_for_employee(args.employee_pin)
    elif getattr(args, "date", None):
        target_date = _parse_date(args.date)
        exceptions = bundle.schedule_exception_repo.list_for_date(target_date)
    else:
        exceptions = bundle.schedule_exception_repo.list_all()

    if not exceptions:
        print(f"{yellow('No se encontraron excepciones o eventualidades de horario registradas.')}")
        return 0

    shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all() if s.id is not None}
    emp_map = {e.pin: e.full_name for e in bundle.employee_repo.list_all()}

    headers = ["ID", "PIN", "Colaborador", "Fecha", "Tipo de Eventualidad", "Motivo"]
    rows = []
    for exc in exceptions:
        collab_name = emp_map.get(exc.employee_pin, "-")
        if exc.shift_definition_id is None:
            efecto = yellow("DESCANSO (OFF)")
        else:
            s_name = shifts_map.get(exc.shift_definition_id, f"Turno #{exc.shift_definition_id}")
            efecto = cyan(f"Turno: {s_name}")

        rows.append([
            str(exc.id or "-"),
            exc.employee_pin,
            collab_name,
            exc.date.isoformat(),
            efecto,
            exc.reason or "-",
        ])

    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "center", "left", "left"]))
    print(f"\n{bold('Total eventualidades:')} {len(exceptions)}")
    return 0


def cmd_schedule_exception_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina o revoca una excepción/eventualidad de horario."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.schedule_exception_repo:
        print(f"{red('✘ Error:')} Repositorio de excepciones no disponible.", file=sys.stderr)
        return 1

    exc = bundle.schedule_exception_repo.get_by_id(args.exception_id)
    if not exc:
        print(f"{red('✘ Error:')} Excepción con ID {args.exception_id} no encontrada.", file=sys.stderr)
        return 1

    success = bundle.schedule_exception_repo.delete(args.exception_id)
    if success:
        print(f"\n{green('✔')} Excepción #{args.exception_id} ({exc.employee_pin} en {exc.date}) eliminada correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar la excepción con ID {args.exception_id}.", file=sys.stderr)
        return 1


# ============================================================================
# 9. Comando Unificado Establecer Horario (asistpy schedule set)
# ============================================================================


def _run_interactive_schedule_wizard(bundle: Any, shifts: dict[int, ShiftDefinition], args: argparse.Namespace) -> int:
    print(f"\n{bold('🧙 Asistente Interactivo de Configuración de Horario')}")
    print("Siga las instrucciones para configurar el rol de turno y días de descanso.\n")

    employees = bundle.employee_repo.list_all()
    if not employees:
        print(f"{red('✘ Error:')} No hay colaboradores registrados en el sistema.", file=sys.stderr)
        return 1

    pin = args.employee_pin
    if not pin:
        print(f"{bold('Colaboradores disponibles:')}")
        for idx, emp in enumerate(employees, start=1):
            print(f"  {idx}) {emp.pin} - {emp.full_name}")
        while True:
            choice = input(f"\nIngrese el PIN o número de colaborador [1-{len(employees)}]: ").strip()
            if not choice:
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(employees):
                emp = employees[int(choice) - 1]
                pin = emp.pin
                break
            found = next((e for e in employees if e.pin.lower() == choice.lower()), None)
            if found:
                emp = found
                pin = emp.pin
                break
            print(f"{yellow('Opción o PIN no válido. Intente de nuevo.')}")
    else:
        emp = bundle.employee_repo.get_by_pin(pin)
        if not emp:
            print(f"{red('✘ Error:')} Colaborador con PIN '{pin}' no encontrado.", file=sys.stderr)
            return 1

    print(f"✔ Colaborador seleccionado: {cyan(emp.full_name)} ({emp.pin})")

    valid_from_default = date.today().isoformat()
    inp_from = input(f"\nFecha de inicio de vigencia [{valid_from_default}]: ").strip()
    valid_from = _parse_date(inp_from) if inp_from else date.today()

    inp_until = input("Fecha de fin de vigencia (opcional, ENTER para indefinido): ").strip()
    valid_until = _parse_date(inp_until) if inp_until else None

    print(f"\n{bold('Seleccione el tipo de turno:')}")
    print("  1) Turno Fijo (un solo turno)")
    print("  2) Turnos Rotativos (lista ordenada de turnos periódicos)")
    shift_mode_choice = input("Opción [1-2] (predeterminado 1): ").strip() or "1"

    if shift_mode_choice == "2":
        shift_mode = ShiftModeOption.ROTATING
        fixed_shift_id = None
        print(f"\n{bold('Turnos disponibles en catálogo:')}")
        for s in shifts.values():
            st = s.start_time.strftime("%H:%M") if s.start_time else "N/A"
            et = s.end_time.strftime("%H:%M") if s.end_time else "N/A"
            print(f"  ID {s.id}: {s.name} ({st} - {et})")
        while True:
            inp_rot = input("Ingrese los IDs de turnos a rotar separados por coma (ej. '1,2'): ").strip()
            try:
                rot_ids = [int(x.strip()) for x in inp_rot.split(",") if x.strip()]
                if rot_ids and all(sid in shifts for sid in rot_ids):
                    break
            except ValueError:
                pass
            print(f"{yellow('Secuencia inválida o algún ID de turno no existe. Intente de nuevo.')}")

        print("\nFrecuencia de rotación de turno:")
        print("  1) Cada semana")
        print("  2) Cada 2 semanas (quincenal)")
        print("  3) Cada mes")
        freq_choice = input("Opción [1-3] (predeterminado 1): ").strip() or "1"
        shift_freq_weeks = 2 if freq_choice == "2" else (4 if freq_choice == "3" else 1)
    else:
        shift_mode = ShiftModeOption.FIXED
        rot_ids = None
        shift_freq_weeks = 1
        print(f"\n{bold('Turnos disponibles en catálogo:')}")
        for s in shifts.values():
            st = s.start_time.strftime("%H:%M") if s.start_time else "N/A"
            et = s.end_time.strftime("%H:%M") if s.end_time else "N/A"
            print(f"  ID {s.id}: {s.name} ({st} - {et})")
        while True:
            inp_shift = input("Ingrese el ID del turno fijo asignado: ").strip()
            if inp_shift.isdigit() and int(inp_shift) in shifts:
                fixed_shift_id = int(inp_shift)
                break
            print(f"{yellow('ID de turno no válido. Intente de nuevo.')}")

    print(f"\n{bold('Seleccione el esquema de días de descanso:')}")
    print("  1) Descanso Fijo Semanal (ej. Domingos o Sábado y Domingo)")
    print("  2) Se recorre al siguiente día (Descanso Rolado continuo)")
    print("  3) Días fijos de cambio / alternado (ej. semana 1 domingo, semana 2 sábado)")
    print("  4) Ciclo continuo de trabajo x descanso (ej. 6x1, 4x2)")
    rest_choice = input("Opción [1-4] (predeterminado 1): ").strip() or "1"

    if rest_choice == "2":
        rest_mode = RestModeOption.ROLLING
        fixed_rest = None
        alt_days = None
        alt_freq = 1
        cyc_work = 6
        cyc_rest = 1
        inp_start = input("Día inicial en que empieza descansando [domingo]: ").strip() or "domingo"
        rolling_start = DAY_NAME_MAP.get(inp_start.lower(), Weekday.SUNDAY).value
        inp_interval = input("Cada cuántas semanas se recorre al siguiente día [1]: ").strip() or "1"
        rolling_interval = int(inp_interval) if inp_interval.isdigit() else 1

    elif rest_choice == "3":
        rest_mode = RestModeOption.ALTERNATING
        fixed_rest = None
        rolling_start = 6
        rolling_interval = 1
        cyc_work = 6
        cyc_rest = 1
        inp_alt = input("Días a alternar separados por coma [domingo,sabado]: ").strip() or "domingo,sabado"
        alt_days = [DAY_NAME_MAP[x.strip().lower()].value for x in inp_alt.split(",") if x.strip().lower() in DAY_NAME_MAP]
        if not alt_days:
            alt_days = [6, 5]
        inp_alt_freq = input("Cada cuántas semanas alterna de día [1]: ").strip() or "1"
        alt_freq = int(inp_alt_freq) if inp_alt_freq.isdigit() else 1

    elif rest_choice == "4":
        rest_mode = RestModeOption.WORK_REST_CYCLE
        fixed_rest = None
        rolling_start = 6
        rolling_interval = 1
        alt_days = None
        alt_freq = 1
        inp_w = input("Días de trabajo continuo [6]: ").strip() or "6"
        inp_r = input("Días de descanso continuo [1]: ").strip() or "1"
        cyc_work = int(inp_w) if inp_w.isdigit() else 6
        cyc_rest = int(inp_r) if inp_r.isdigit() else 1

    else:
        rest_mode = RestModeOption.FIXED
        rolling_start = 6
        rolling_interval = 1
        alt_days = None
        alt_freq = 1
        cyc_work = 6
        cyc_rest = 1
        inp_rest = input("Día(s) de descanso semanal separados por coma [domingo]: ").strip() or "domingo"
        rest_set = _parse_days_list(inp_rest)
        fixed_rest = {d.value for d in rest_set}

    config = SchedulePlanConfig(
        employee_pin=pin,
        valid_from=valid_from,
        valid_until=valid_until,
        shift_mode=shift_mode,
        fixed_shift_id=fixed_shift_id,
        rotating_shift_ids=rot_ids,
        shift_frequency_weeks=shift_freq_weeks,
        rest_mode=rest_mode,
        fixed_rest_weekdays=fixed_rest,
        rolling_initial_weekday=rolling_start,
        rolling_interval_weeks=rolling_interval,
        alternating_rest_weekdays=alt_days,
        alternating_interval_weeks=alt_freq,
        cycle_work_days=cyc_work,
        cycle_rest_days=cyc_rest,
    )

    try:
        SchedulePlanBuilder.validate_config(config, shifts)
    except ValidationError as e:
        print(f"\n{red('✘ Error de validación:')} {e}", file=sys.stderr)
        return 1

    preview_days = 21
    preview = SchedulePlanBuilder.generate_preview(config, shifts, days=preview_days)
    print(f"\n{bold('📅 Proyección de Rol de Turnos')} (Próximos {preview_days} días para {cyan(emp.full_name)}):")
    headers = ["Fecha", "Día", "Turno Programado", "Horario", "Estado"]
    rows = []
    work_count = 0
    rest_count = 0
    for p in preview:
        if p.is_rest_day:
            rest_count += 1
            status_str = yellow("DESCANSO")
            shift_col = yellow(p.shift_name)
        else:
            work_count += 1
            status_str = green("LABORABLE")
            shift_col = p.shift_name

        rows.append([
            p.date.isoformat(),
            p.day_name,
            shift_col,
            p.time_range_str,
            status_str,
        ])

    print(render_table(headers, rows))
    print(f"  • {green(str(work_count))} días laborables | {yellow(str(rest_count))} días de descanso.\n")

    confirm = input(f"{bold('¿Desea aplicar y guardar este horario?')} [S/n]: ").strip().lower()
    if confirm not in ("", "s", "si", "y", "yes"):
        print(f"{yellow('Operación cancelada por el usuario.')}")
        return 0

    prefix = f"Rol {emp.full_name}"
    assignment, pattern = SchedulePlanBuilder.build_assignment_and_pattern(
        config, shifts, pattern_name_prefix=prefix
    )

    if pattern is not None:
        saved_pattern = bundle.rotation_pattern_repo.save(pattern)
        assignment.rotation_pattern_id = saved_pattern.id

    saved_assign = bundle.schedule_assignment_repo.save(assignment)
    print(f"\n{green('✔')} Horario y descansos establecidos exitosamente con ID {bold(str(saved_assign.id))}.")
    print(f"  • Colaborador: {bold(emp.full_name)} ({emp.pin})")
    print(f"  • Modo: {bold(saved_assign.mode.value.upper())}")
    if pattern is not None:
        print(f"  • Patrón generado: {cyan(pattern.name)} (#{saved_pattern.id})")
    print(f"  • Vigencia desde: {bold(saved_assign.valid_from.isoformat())}")
    return 0


def cmd_schedule_set(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Establece horario y descansos (fijos/rotativos/rolados) con previsualización."""
    bundle = ctx.get_bundle(init_tables=True)
    shifts = {s.id: s for s in bundle.shift_repo.list_all() if s.id is not None}

    if getattr(args, "interactive", False):
        return _run_interactive_schedule_wizard(bundle, shifts, args)

    if not args.employee_pin:
        print(f"{red('✘ Error:')} Debe especificar --employee-pin (o usar --interactive).", file=sys.stderr)
        return 1

    emp = bundle.employee_repo.get_by_pin(args.employee_pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.employee_pin}' no encontrado.", file=sys.stderr)
        return 1

    valid_from = _parse_date(args.valid_from) if args.valid_from else date.today()
    valid_until = _parse_date(args.valid_until) if args.valid_until else None

    # Esquema de turno
    if getattr(args, "rotating_shifts", None):
        shift_mode = ShiftModeOption.ROTATING
        fixed_shift_id = None
        try:
            rot_ids = [int(x.strip()) for x in args.rotating_shifts.split(",") if x.strip()]
        except ValueError:
            print(f"{red('✘ Error:')} Formato inválido en --rotating-shifts. Use IDs separados por coma (ej. '1,2').", file=sys.stderr)
            return 1
        freq_map = {"weekly": 1, "biweekly": 2, "monthly": 4}
        shift_freq_weeks = freq_map.get((args.shift_freq or "weekly").lower(), getattr(args, "shift_freq_weeks", None) or 1)
    else:
        shift_mode = ShiftModeOption.FIXED
        if args.shift_id is None:
            print(f"{red('✘ Error:')} Debe especificar --shift-id (o --rotating-shifts para rotación).", file=sys.stderr)
            return 1
        fixed_shift_id = args.shift_id
        rot_ids = None
        shift_freq_weeks = 1

    # Esquema de descanso
    if getattr(args, "rolling_rest", False):
        rest_mode = RestModeOption.ROLLING
        fixed_rest = None
        start_day_str = (args.rolling_start or "domingo").lower().strip()
        if start_day_str not in DAY_NAME_MAP:
            print(f"{red('✘ Error:')} Día inicial no reconocido en --rolling-start: '{start_day_str}'.", file=sys.stderr)
            return 1
        rolling_start = DAY_NAME_MAP[start_day_str].value
        rolling_interval = getattr(args, "rolling_interval", None) or 1
        alt_days = None
        alt_freq = 1
        cyc_work = 6
        cyc_rest = 1
    elif getattr(args, "alternating_rest", None):
        rest_mode = RestModeOption.ALTERNATING
        fixed_rest = None
        rolling_start = 6
        rolling_interval = 1
        alt_day_names = [x.strip().lower() for x in args.alternating_rest.split(",") if x.strip()]
        alt_days = []
        for d in alt_day_names:
            if d not in DAY_NAME_MAP:
                print(f"{red('✘ Error:')} Día no reconocido en --alternating-rest: '{d}'.", file=sys.stderr)
                return 1
            alt_days.append(DAY_NAME_MAP[d].value)
        alt_freq = getattr(args, "alt_interval", None) or 1
        cyc_work = 6
        cyc_rest = 1
    elif getattr(args, "cycle_rest", None) or (getattr(args, "work_days", None) is not None and getattr(args, "rest_days_count", None) is not None):
        rest_mode = RestModeOption.WORK_REST_CYCLE
        fixed_rest = None
        rolling_start = 6
        rolling_interval = 1
        alt_days = None
        alt_freq = 1
        if args.cycle_rest:
            try:
                parts = args.cycle_rest.lower().split("x")
                cyc_work = int(parts[0])
                cyc_rest = int(parts[1])
            except Exception:
                print(f"{red('✘ Error:')} Formato inválido en --cycle-rest. Use formato NxM (ej. '6x1', '4x2').", file=sys.stderr)
                return 1
        else:
            cyc_work = args.work_days
            cyc_rest = args.rest_days_count
    else:
        rest_mode = RestModeOption.FIXED
        if getattr(args, "rest_days", None):
            try:
                rest_weekdays_set = _parse_days_list(args.rest_days)
                fixed_rest = {d.value for d in rest_weekdays_set}
            except argparse.ArgumentTypeError as e:
                print(f"{red('✘ Error:')} {e}", file=sys.stderr)
                return 1
        else:
            fixed_rest = {6}  # Domingo por defecto
        rolling_start = 6
        rolling_interval = 1
        alt_days = None
        alt_freq = 1
        cyc_work = 6
        cyc_rest = 1

    config = SchedulePlanConfig(
        employee_pin=args.employee_pin,
        valid_from=valid_from,
        valid_until=valid_until,
        shift_mode=shift_mode,
        fixed_shift_id=fixed_shift_id,
        rotating_shift_ids=rot_ids,
        shift_frequency_weeks=shift_freq_weeks,
        rest_mode=rest_mode,
        fixed_rest_weekdays=fixed_rest,
        rolling_initial_weekday=rolling_start,
        rolling_interval_weeks=rolling_interval,
        alternating_rest_weekdays=alt_days,
        alternating_interval_weeks=alt_freq,
        cycle_work_days=cyc_work,
        cycle_rest_days=cyc_rest,
    )

    try:
        SchedulePlanBuilder.validate_config(config, shifts)
    except ValidationError as e:
        print(f"{red('✘ Error de validación:')} {e}", file=sys.stderr)
        return 1

    preview_days = getattr(args, "preview_days", None) or 14
    preview = SchedulePlanBuilder.generate_preview(config, shifts, days=preview_days)

    print(f"\n{bold('📅 Proyección de Rol de Turnos')} (Próximos {preview_days} días para {cyan(emp.full_name)}):")
    headers = ["Fecha", "Día", "Turno Programado", "Horario", "Estado"]
    rows = []
    work_count = 0
    rest_count = 0
    for p in preview:
        if p.is_rest_day:
            rest_count += 1
            status_str = yellow("DESCANSO")
            shift_col = yellow(p.shift_name)
        else:
            work_count += 1
            status_str = green("LABORABLE")
            shift_col = p.shift_name

        rows.append([
            p.date.isoformat(),
            p.day_name,
            shift_col,
            p.time_range_str,
            status_str,
        ])

    print(render_table(headers, rows, alignments=["center", "left", "left", "left", "center"]))
    print(f"  • {green(str(work_count))} días laborables | {yellow(str(rest_count))} días de descanso.\n")

    if getattr(args, "preview_only", False):
        print(f"{cyan('ℹ')} Modo de solo previsualización. No se realizaron cambios en la base de datos.")
        return 0

    prefix = f"Rol {emp.full_name}"
    assignment, pattern = SchedulePlanBuilder.build_assignment_and_pattern(
        config, shifts, pattern_name_prefix=prefix
    )

    if pattern is not None:
        saved_pattern = bundle.rotation_pattern_repo.save(pattern)
        assignment.rotation_pattern_id = saved_pattern.id

    saved_assign = bundle.schedule_assignment_repo.save(assignment)
    print(f"{green('✔')} Horario y descansos establecidos exitosamente con ID {bold(str(saved_assign.id))}.")
    print(f"  • Colaborador: {bold(emp.full_name)} ({emp.pin})")
    print(f"  • Modo: {bold(saved_assign.mode.value.upper())}")
    if pattern is not None:
        print(f"  • Patrón generado: {cyan(pattern.name)} (#{saved_pattern.id})")
    print(f"  • Vigencia desde: {bold(saved_assign.valid_from.isoformat())}")
    return 0


# ============================================================================
# Registro de Subparsers
# ============================================================================


def register_schedule_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy schedule`."""
    sched_parser = subparsers.add_parser(
        "schedule",
        help="Gestión y asignación de horarios, descansos fijos/rotativos y eventualidades",
        description="Permite asignar turnos fijos o rotativos a empleados, definir descansos semanales y registrar eventualidades de calendario.",
    )
    sched_subparsers = sched_parser.add_subparsers(dest="schedule_action", required=True)

    # 0. asistpy schedule set (Comando principal unificado)
    set_parser = sched_subparsers.add_parser(
        "set",
        parents=[get_common_parser()],
        help="Establece horario y descansos (fijos, rotativos, rolados o ciclos) con previsualización",
        description="Configura de forma integral el horario del empleado con descansos fijos o rotativos y previsualización en consola.",
    )
    set_parser.add_argument("--employee-pin", help="PIN del colaborador")
    set_parser.add_argument("--valid-from", help="Fecha inicial YYYY-MM-DD (predeterminada: hoy)")
    set_parser.add_argument("--valid-until", help="Fecha final YYYY-MM-DD (opcional)")

    # Turnos
    set_parser.add_argument("--shift-id", type=int, help="ID del turno fijo asignado")
    set_parser.add_argument(
        "--rotating-shifts",
        help="IDs de turnos a rotar separados por comas (ej. '1,2')",
    )
    set_parser.add_argument(
        "--shift-freq",
        choices=["weekly", "biweekly", "monthly"],
        default="weekly",
        help="Frecuencia de rotación de turno (predeterminado: weekly)",
    )
    set_parser.add_argument(
        "--shift-freq-weeks",
        type=int,
        help="Semanas por cada turno en rotación",
    )

    # Descansos
    set_parser.add_argument(
        "--rest-days",
        help="Días de descanso semanal fijo (ej. 'domingo', 'sab,dom')",
    )
    set_parser.add_argument(
        "--rolling-rest",
        action="store_true",
        help="Activa descanso que se recorre al siguiente día cada ciclo",
    )
    set_parser.add_argument(
        "--rolling-start",
        default="domingo",
        help="Día inicial en que empieza descansando (predeterminado: domingo)",
    )
    set_parser.add_argument(
        "--rolling-interval",
        type=int,
        default=1,
        help="Cada cuántas semanas se recorre al siguiente día (predeterminado: 1)",
    )
    set_parser.add_argument(
        "--alternating-rest",
        help="Días a alternar semana con semana (ej. 'domingo,sabado')",
    )
    set_parser.add_argument(
        "--alt-interval",
        type=int,
        default=1,
        help="Cada cuántas semanas alterna de día (predeterminado: 1)",
    )
    set_parser.add_argument(
        "--cycle-rest",
        help="Ciclo continuo de trabajo x descanso en formato NxM (ej. '6x1', '4x2')",
    )
    set_parser.add_argument("--work-days", type=int, help="Días de trabajo continuo en ciclo")
    set_parser.add_argument("--rest-days-count", type=int, help="Días de descanso continuo en ciclo")

    # Previsualización e interactivo
    set_parser.add_argument(
        "--preview-days",
        type=int,
        default=14,
        help="Días de proyección a previsualizar en terminal (predeterminado: 14)",
    )
    set_parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Solo muestra la tabla de previsualización sin guardar cambios en BD",
    )
    set_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Inicia el asistente interactivo paso a paso por consola",
    )
    set_parser.set_defaults(func=cmd_schedule_set)

    # 1. asistpy schedule assign
    assign_parser = sched_subparsers.add_parser(
        "assign",
        parents=[get_common_parser()],
        help="Asigna un turno laboral o esquema rotativo a un empleado",
    )
    assign_parser.add_argument("--employee-pin", required=True, help="PIN del empleado (ej. 'E100')")
    assign_parser.add_argument("--shift-id", type=int, help="ID del turno a asignar (requerido si mode es fixed)")
    assign_parser.add_argument(
        "--rotation-pattern-id",
        type=int,
        help="ID del patrón de rotación (requerido si mode es rotating)",
    )
    assign_parser.add_argument(
        "--mode",
        choices=["fixed", "rotating", "open"],
        default="fixed",
        help="Modo de horario (predeterminado: fixed)",
    )
    assign_parser.add_argument(
        "--rest-days",
        help="Días de descanso separados por comas (ej. 'domingo' o 'sab,dom' o 'sunday')",
    )
    assign_parser.add_argument(
        "--working-days",
        help="Días laborables separados por comas (ej. 'lun,mar,mie,jue,vie')",
    )
    assign_parser.add_argument("--valid-from", help="Fecha de inicio YYYY-MM-DD (predeterminada: hoy)")
    assign_parser.add_argument("--valid-until", help="Fecha límite de vigencia YYYY-MM-DD (opcional)")
    assign_parser.set_defaults(func=cmd_schedule_assign)

    # 2. asistpy schedule show
    show_parser = sched_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle de una asignación de horario",
    )
    show_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación")
    show_parser.set_defaults(func=cmd_schedule_show)

    # 3. asistpy schedule list
    list_parser = sched_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista las asignaciones de horario activas",
    )
    list_parser.add_argument("--employee-pin", help="Filtrar por PIN del empleado")
    list_parser.set_defaults(func=cmd_schedule_list)

    # 4. asistpy schedule edit
    edit_parser = sched_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los parámetros de una asignación de horario",
    )
    edit_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a modificar")
    edit_parser.add_argument("--shift-id", type=int, help="Nuevo ID de turno asignado")
    edit_parser.add_argument("--rotation-pattern-id", type=int, help="Nuevo ID de patrón de rotación")
    edit_parser.add_argument("--mode", choices=["fixed", "rotating", "open"], help="Nuevo modo de horario")
    edit_parser.add_argument("--rest-days", help="Nuevos días de descanso (ej. 'domingo')")
    edit_parser.add_argument("--working-days", help="Nuevos días laborables (ej. 'lun,mar,mie,jue,vie')")
    edit_parser.add_argument("--valid-from", help="Nueva fecha de inicio YYYY-MM-DD")
    edit_parser.add_argument("--valid-until", help="Nueva fecha de término YYYY-MM-DD")
    edit_parser.set_defaults(func=cmd_schedule_edit)

    # 5. asistpy schedule close
    close_parser = sched_subparsers.add_parser(
        "close",
        parents=[get_common_parser()],
        help="Cierra la vigencia de una asignación de horario",
    )
    close_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a cerrar")
    close_parser.add_argument("--valid-until", help="Fecha de cierre YYYY-MM-DD (predeterminada: hoy)")
    close_parser.set_defaults(func=cmd_schedule_close)

    # 6. asistpy schedule delete
    del_parser = sched_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina una asignación de horario",
    )
    del_parser.add_argument("--assignment-id", type=int, required=True, help="ID de la asignación a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_schedule_delete)

    # 7. asistpy schedule rotation (subcomandos de patrones)
    rot_parser = sched_subparsers.add_parser(
        "rotation",
        help="Administra el catálogo de patrones de rotación de turnos (6x1, 5x2, etc.)",
    )
    rot_subparsers = rot_parser.add_subparsers(dest="rotation_action", required=True)

    rot_add = rot_subparsers.add_parser("add", parents=[get_common_parser()], help="Crea un nuevo patrón rotativo")
    rot_add.add_argument("--name", required=True, help="Nombre del patrón (ej. '6x1 Matutino')")
    rot_add.add_argument(
        "--sequence",
        required=True,
        help="Secuencia cíclica de turnos y descansos separada por comas (ej. '1,1,1,1,1,1,OFF' o '1,OFF,2,OFF')",
    )
    rot_add.add_argument(
        "--frequency",
        choices=["daily", "weekly", "biweekly", "monthly"],
        default="daily",
        help="Frecuencia del período (predeterminado: daily)",
    )
    rot_add.add_argument("--anchor-date", help="Fecha ancla de inicio del ciclo YYYY-MM-DD (predeterminado: hoy)")
    rot_add.set_defaults(func=cmd_schedule_rotation_add)

    rot_list = rot_subparsers.add_parser("list", parents=[get_common_parser()], help="Lista patrones rotativos")
    rot_list.set_defaults(func=cmd_schedule_rotation_list)

    rot_show = rot_subparsers.add_parser("show", parents=[get_common_parser()], help="Muestra detalle de un patrón")
    rot_show.add_argument("--pattern-id", type=int, required=True, help="ID del patrón")
    rot_show.set_defaults(func=cmd_schedule_rotation_show)

    rot_del = rot_subparsers.add_parser("delete", parents=[get_common_parser()], help="Elimina un patrón rotativo")
    rot_del.add_argument("--pattern-id", type=int, required=True, help="ID del patrón a eliminar")
    rot_del.set_defaults(func=cmd_schedule_rotation_delete)

    # 8. asistpy schedule exception (subcomandos de eventualidades)
    exc_parser = sched_subparsers.add_parser(
        "exception",
        help="Registra eventualidades o excepciones puntuales de horario (forzar descanso o turno)",
    )
    exc_subparsers = exc_parser.add_subparsers(dest="exception_action", required=True)

    exc_add = exc_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra una eventualidad de horario para un empleado en una fecha",
    )
    exc_add.add_argument("--employee-pin", required=True, help="PIN del colaborador")
    exc_add.add_argument("--date", required=True, help="Fecha de la eventualidad YYYY-MM-DD")
    exc_group = exc_add.add_mutually_exclusive_group(required=True)
    exc_group.add_argument("--rest-day", action="store_true", help="Forzar día de descanso obligatorio (OFF)")
    exc_group.add_argument("--shift-id", type=int, help="Forzar turno específico sustituyendo el habitual")
    exc_add.add_argument("--reason", help="Motivo de la eventualidad (ej. 'Cambio de descanso acordado')")
    exc_add.set_defaults(func=cmd_schedule_exception_add)

    exc_list = exc_subparsers.add_parser("list", parents=[get_common_parser()], help="Lista eventualidades de horario")
    exc_list.add_argument("--employee-pin", help="Filtrar por PIN de colaborador")
    exc_list.add_argument("--date", help="Filtrar por fecha puntual YYYY-MM-DD")
    exc_list.set_defaults(func=cmd_schedule_exception_list)

    exc_del = exc_subparsers.add_parser("delete", parents=[get_common_parser()], help="Elimina una eventualidad")
    exc_del.add_argument("--exception-id", type=int, required=True, help="ID de la eventualidad a eliminar")
    exc_del.set_defaults(func=cmd_schedule_exception_delete)

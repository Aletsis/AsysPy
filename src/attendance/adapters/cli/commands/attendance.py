"""Comandos de evaluación, consulta y ajuste de asistencia (`asistpy attendance`)."""

import argparse
import getpass
import sys
from datetime import date, datetime

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.application.adjustment.adjust_punch import (
    create_manual_punch,
    modify_punch_timestamp,
)
from attendance.application.attendance.process_daily_attendance import (
    ProcessDailyAttendance,
    ProcessDailyAttendanceBatch,
    ProcessEmployeeAttendanceRange,
)
from attendance.domain.attendance import DailyAttendance


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido '{val}'. Use YYYY-MM-DD.")


def _parse_datetime(val: str) -> datetime:
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Formato de fecha y hora inválido '{val}'. Use 'YYYY-MM-DD HH:MM:SS'."
            )


def _format_minutes(minutes: int) -> str:
    """Convierte minutos enteros en representación legible (ej. 8h 30m o 45m)."""
    if minutes <= 0:
        return "0m"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _format_daily_status(status_val: str) -> str:
    s = str(status_val).upper()
    if "PRESENT" in s:
        return green("PRESENTE")
    elif "ABSENT" in s:
        return red("FALTA")
    elif "JUSTIFIED" in s:
        return yellow("JUSTIFICADA")
    elif "HOLIDAY" in s:
        return cyan("FESTIVO")
    elif "REST" in s:
        return yellow("DESCANSO")
    return s


def cmd_attendance_evaluate(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Evalúa la asistencia diaria para uno o todos los empleados."""
    bundle = ctx.get_bundle(init_tables=False)

    target_date = _parse_date(args.date) or date.today()
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    mark_logs = not args.no_mark_processed
    is_holiday = args.holiday

    daily_processor = ProcessDailyAttendance(
        attendance_repo=bundle.attendance_repo,
        daily_attendance_repo=bundle.daily_attendance_repo,
        schedule_assignment_repo=bundle.schedule_assignment_repo,
        shift_repo=bundle.shift_repo,
        rotation_pattern_repo=bundle.rotation_pattern_repo,
        incidence_repo=bundle.incidence_repo,
        schedule_exception_repo=bundle.schedule_exception_repo,
    )

    results: list[DailyAttendance] = []

    try:
        # Caso 1: Rango de fechas para un empleado
        if args.employee_pin and start_date and end_date:
            print(f"Evaluando asistencia de empleado {bold(args.employee_pin)} del {start_date} al {end_date}...")
            range_proc = ProcessEmployeeAttendanceRange(daily_processor=daily_processor)
            results = range_proc.execute(
                employee_pin=args.employee_pin,
                start_date=start_date,
                end_date=end_date,
                mark_logs_processed=mark_logs,
            )

        # Caso 2: Fecha única para un empleado
        elif args.employee_pin:
            print(f"Evaluando asistencia de empleado {bold(args.employee_pin)} al {target_date}...")
            daily = daily_processor.execute(
                employee_pin=args.employee_pin,
                target_date=target_date,
                is_holiday=is_holiday,
                mark_logs_processed=mark_logs,
            )
            results = [daily]

        # Caso 3: Lote completo de empleados activos en una fecha
        else:
            print(f"Evaluando jornada en lote para empleados activos al {bold(str(target_date))}...")
            batch_proc = ProcessDailyAttendanceBatch(
                employee_repo=bundle.employee_repo,
                daily_processor=daily_processor,
            )
            results = batch_proc.execute(
                target_date=target_date,
                branch_id=args.branch_id,
                is_holiday=is_holiday,
                mark_logs_processed=mark_logs,
            )

        if not results:
            print(f"{yellow('No se obtuvieron registros evaluados para los criterios especificados.')}")
            return 0

        headers = [
            "PIN",
            "Fecha",
            "Turno Esperado",
            "Entrada",
            "Salida",
            "Trabajado",
            "Retardo",
            "Salida Ant.",
            "Horas Extra",
            "Estado",
        ]
        rows = []
        for r in results:
            shift_name = r.expected_shift.name if r.expected_shift else "Sin Asignar"
            in_time = r.first_check_in.strftime("%H:%M:%S") if r.first_check_in else "--:--:--"
            out_time = r.last_check_out.strftime("%H:%M:%S") if r.last_check_out else "--:--:--"
            status_str = _format_daily_status(str(r.status.value if hasattr(r.status, "value") else r.status))

            tardiness_str = _format_minutes(r.tardiness_minutes)
            if r.tardiness_minutes > 0:
                tardiness_str = yellow(tardiness_str)

            early_str = _format_minutes(r.early_departure_minutes)
            if r.early_departure_minutes > 0:
                early_str = yellow(early_str)

            ot_str = _format_minutes(r.overtime_minutes)
            if r.overtime_minutes > 0:
                ot_str = cyan(ot_str)

            rows.append([
                r.employee_pin,
                str(r.date),
                shift_name,
                in_time,
                out_time,
                _format_minutes(r.total_worked_minutes),
                tardiness_str,
                early_str,
                ot_str,
                status_str,
            ])

        table = render_table(
            headers=headers,
            rows=rows,
            alignments=["left", "center", "left", "center", "center", "right", "right", "right", "right", "center"],
        )
        print("\n" + table)
        print(f"\n{green('✔ Evaluación completada.')} Total registros evaluados: {bold(str(len(results)))}")
        return 0

    except Exception as e:
        print(f"{red('✘ Error al procesar asistencia:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def cmd_attendance_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista registros de asistencia calculada o marcaciones crudas."""
    bundle = ctx.get_bundle(init_tables=False)

    limit = args.limit or 50

    try:
        # Caso A: Marcaciones crudas
        if args.raw:
            logs = bundle.attendance_repo.list_all()
            if args.employee_pin:
                logs = [log_item for log_item in logs if log_item.employee_pin == args.employee_pin]
            if args.date:
                t_date = _parse_date(args.date)
                logs = [log_item for log_item in logs if log_item.timestamp.date() == t_date]

            logs = logs[-limit:]

            if not logs:
                print(f"{yellow('No se encontraron marcaciones crudas con los criterios especificados.')}")
                return 0

            headers = ["ID", "UID", "PIN Empleado", "Fecha / Hora", "Método", "Estatus Procesamiento"]
            rows = []
            for log_item in logs:
                rows.append([
                    str(log_item.id or "-"),
                    str(log_item.record_uid),
                    log_item.employee_pin,
                    log_item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    str(log_item.auth_method.name if hasattr(log_item.auth_method, "name") else log_item.auth_method),
                    str(log_item.processing_status.name if hasattr(log_item.processing_status, "name") else log_item.processing_status),
                ])

            print(render_table(headers=headers, rows=rows, alignments=["right", "right", "left", "center", "center", "center"]))
            print(f"\n{bold('Total mostrados:')} {len(logs)}")
            return 0

        # Caso B: Jornadas diarias evaluadas
        dailies = bundle.daily_attendance_repo.list_all()
        if args.employee_pin:
            dailies = [d for d in dailies if d.employee_pin == args.employee_pin]
        if args.date:
            t_date = _parse_date(args.date)
            dailies = [d for d in dailies if d.date == t_date]
        if args.start_date and args.end_date:
            s_date = _parse_date(args.start_date)
            e_date = _parse_date(args.end_date)
            if s_date and e_date:
                dailies = [d for d in dailies if s_date <= d.date <= e_date]

        dailies = dailies[-limit:]

        if not dailies:
            print(f"{yellow('No se encontraron jornadas evaluadas con los criterios especificados.')}")
            return 0

        headers = ["PIN", "Fecha", "Entrada", "Salida", "Trabajado", "Retardo", "Horas Extra", "Estado"]
        rows = []
        for d in dailies:
            in_t = d.first_check_in.strftime("%H:%M:%S") if d.first_check_in else "--:--:--"
            out_t = d.last_check_out.strftime("%H:%M:%S") if d.last_check_out else "--:--:--"
            status_str = _format_daily_status(str(d.status.value if hasattr(d.status, "value") else d.status))
            rows.append([
                d.employee_pin,
                str(d.date),
                in_t,
                out_t,
                _format_minutes(d.total_worked_minutes),
                _format_minutes(d.tardiness_minutes),
                _format_minutes(d.overtime_minutes),
                status_str,
            ])

        print(render_table(headers=headers, rows=rows, alignments=["left", "center", "center", "center", "right", "right", "right", "center"]))
        print(f"\n{bold('Total mostrados:')} {len(dailies)}")
        return 0

    except Exception as e:
        print(f"{red('✘ Error al consultar asistencias:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def cmd_attendance_adjust(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Realiza un ajuste manual de marcación con trazabilidad obligatoria de auditoría."""
    bundle = ctx.get_bundle(init_tables=False)

    modified_by = args.modified_by or getpass.getuser() or "admin_cli"
    new_timestamp = _parse_datetime(args.timestamp)
    reason = args.reason

    try:
        # Si se especificó un log_id, se modifica una marcación existente
        if args.log_id is not None:
            print(f"Modificando marcación ID {bold(str(args.log_id))} a nueva fecha {new_timestamp}...")
            updated_log = modify_punch_timestamp(
                log_id=args.log_id,
                new_timestamp=new_timestamp,
                performed_by=modified_by,
                reason=reason,
                attendance_repo=bundle.attendance_repo,
                audit_repo=bundle.audit_repo,
            )
            print(f"\n{green('✔ Marcación modificada exitosamente.')}")
            print(f"  • Marcación ID: {bold(str(updated_log.id))}")
            print(f"  • Empleado: {bold(updated_log.employee_pin)}")
            print(f"  • Nueva Fecha/Hora: {bold(str(updated_log.timestamp))}")
            print(f"  • Estado: {yellow('Reestablecido a RAW para reevaluación')}")
            print(f"  • Registrado en Auditoría por: {cyan(modified_by)}")
            return 0

        # Si no se pasó log_id, se crea una nueva marcación manual
        if not args.employee_pin:
            print(f"{red('✘ Error:')} Para crear una marcación manual se requiere el parámetro --employee-pin.", file=sys.stderr)
            return 1

        print(f"Creando marcación manual para empleado {bold(args.employee_pin)} al {new_timestamp}...")
        created_log = create_manual_punch(
            employee_pin=args.employee_pin,
            timestamp=new_timestamp,
            performed_by=modified_by,
            reason=reason,
            attendance_repo=bundle.attendance_repo,
            audit_repo=bundle.audit_repo,
            device_id=args.device_id or 0,
        )
        print(f"\n{green('✔ Marcación manual creada exitosamente.')}")
        print(f"  • Marcación ID: {bold(str(created_log.id or 'Nuevo'))}")
        print(f"  • Empleado: {bold(created_log.employee_pin)}")
        print(f"  • Fecha/Hora: {bold(str(created_log.timestamp))}")
        print(f"  • Motivo: {reason}")
        print(f"  • Registrado en Auditoría por: {cyan(modified_by)}")
        return 0

    except Exception as e:
        print(f"{red('✘ Error al registrar ajuste manual:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def register_attendance_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy attendance`."""
    att_parser = subparsers.add_parser(
        "attendance",
        help="Evaluación de jornadas, consulta y ajustes de marcaciones",
        description="Evalúa turnos, calcula horas trabajadas, consulta historial y realiza ajustes auditados.",
    )
    att_subparsers = att_parser.add_subparsers(dest="attendance_action", required=True)

    # asistpy attendance evaluate
    eval_parser = att_subparsers.add_parser(
        "evaluate",
        parents=[get_common_parser()],
        help="Evalúa jornadas de asistencia según horarios y turnos",
        description="Ejecuta el motor de evaluación para calcular asistencias, retardos y horas extras.",
    )
    eval_parser.add_argument("--employee-pin", help="PIN del empleado a evaluar")
    eval_parser.add_argument("--date", help="Fecha objetivo (YYYY-MM-DD, predeterminado hoy)")
    eval_parser.add_argument("--start-date", help="Fecha inicial para evaluación en rango (YYYY-MM-DD)")
    eval_parser.add_argument("--end-date", help="Fecha final para evaluación en rango (YYYY-MM-DD)")
    eval_parser.add_argument("--branch-id", type=int, help="Filtrar empleados por sucursal")
    eval_parser.add_argument("--holiday", action="store_true", help="Marcar la fecha como día feriado/festivo")
    eval_parser.add_argument(
        "--no-mark-processed",
        action="store_true",
        help="No marcar las marcaciones crudas como procesadas",
    )
    eval_parser.set_defaults(func=cmd_attendance_evaluate)

    # asistpy attendance list
    list_parser = att_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista jornadas evaluadas o marcaciones crudas",
        description="Consulta los registros de jornada o marcaciones crudas almacenadas.",
    )
    list_parser.add_argument("--employee-pin", help="Filtrar por PIN de empleado")
    list_parser.add_argument("--date", help="Filtrar por fecha específica (YYYY-MM-DD)")
    list_parser.add_argument("--start-date", help="Fecha inicial de rango (YYYY-MM-DD)")
    list_parser.add_argument("--end-date", help="Fecha final de rango (YYYY-MM-DD)")
    list_parser.add_argument("--raw", action="store_true", help="Mostrar marcaciones crudas en lugar de jornadas")
    list_parser.add_argument("--limit", type=int, default=50, help="Número máximo de registros a mostrar (predeterminado 50)")
    list_parser.set_defaults(func=cmd_attendance_list)

    # asistpy attendance adjust
    adjust_parser = att_subparsers.add_parser(
        "adjust",
        parents=[get_common_parser()],
        help="Ajusta o crea una marcación manual con trazabilidad de auditoría",
        description="Permite corregir la hora de una marcación o insertar una manual registrando motivo y responsable.",
    )
    adjust_parser.add_argument("--employee-pin", help="PIN del empleado (requerido para nueva marcación)")
    adjust_parser.add_argument("--log-id", type=int, help="ID de la marcación existente a modificar")
    adjust_parser.add_argument("--timestamp", required=True, help="Fecha y hora del ajuste (YYYY-MM-DD HH:MM:SS)")
    adjust_parser.add_argument("--reason", required=True, help="Motivo obligatorio del ajuste o justificación")
    adjust_parser.add_argument("--modified-by", help="Nombre del usuario que autoriza el ajuste")
    adjust_parser.add_argument("--device-id", type=int, default=0, help="ID de dispositivo para la marcación manual")
    adjust_parser.set_defaults(func=cmd_attendance_adjust)

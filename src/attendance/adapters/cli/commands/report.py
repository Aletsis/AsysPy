"""Comandos de generación y exportación de reportes (`asistpy report`)."""

import argparse
import csv
import io
import json
import sys
from datetime import date
from typing import Any

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.attendance import DailyAttendance


def _parse_date(val: str) -> date:
    try:
        return date.fromisoformat(val)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido '{val}'. Use YYYY-MM-DD.")


def cmd_report_summary(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Genera un reporte consolidado de asistencia en formato tabla, CSV o JSON."""
    bundle = ctx.get_bundle(init_tables=False)

    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date) if args.end_date else start_date

    if end_date < start_date:
        print(f"{red('✘ Error:')} --end-date no puede ser anterior a --start-date.", file=sys.stderr)
        return 1

    try:
        all_records: list[DailyAttendance] = bundle.daily_attendance_repo.list_all()

        # Filtrado en memoria
        filtered: list[DailyAttendance] = []
        for r in all_records:
            if start_date <= r.date <= end_date:
                if args.employee_pin and r.employee_pin != args.employee_pin:
                    continue
                filtered.append(r)

        # Ordenar por empleado y fecha
        filtered.sort(key=lambda x: (x.employee_pin, x.date))

        fmt = (args.format or "table").lower()
        output_data: str = ""

        if fmt == "json":
            json_list: list[dict[str, Any]] = []
            for r in filtered:
                json_list.append({
                    "employee_pin": r.employee_pin,
                    "date": r.date.isoformat(),
                    "expected_shift": r.expected_shift.name if r.expected_shift else None,
                    "first_check_in": r.first_check_in.isoformat() if r.first_check_in else None,
                    "last_check_out": r.last_check_out.isoformat() if r.last_check_out else None,
                    "total_worked_minutes": r.total_worked_minutes,
                    "tardiness_minutes": r.tardiness_minutes,
                    "early_departure_minutes": r.early_departure_minutes,
                    "overtime_minutes": r.overtime_minutes,
                    "status": str(r.status.value if hasattr(r.status, "value") else r.status),
                })
            output_data = json.dumps(json_list, indent=2)

        elif fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                "employee_pin",
                "date",
                "expected_shift",
                "first_check_in",
                "last_check_out",
                "total_worked_minutes",
                "tardiness_minutes",
                "early_departure_minutes",
                "overtime_minutes",
                "status",
            ])
            for r in filtered:
                writer.writerow([
                    r.employee_pin,
                    r.date.isoformat(),
                    r.expected_shift.name if r.expected_shift else "",
                    r.first_check_in.isoformat() if r.first_check_in else "",
                    r.last_check_out.isoformat() if r.last_check_out else "",
                    r.total_worked_minutes,
                    r.tardiness_minutes,
                    r.early_departure_minutes,
                    r.overtime_minutes,
                    str(r.status.value if hasattr(r.status, "value") else r.status),
                ])
            output_data = buf.getvalue()

        else:  # formato 'table'
            if not filtered:
                output_data = yellow(f"No se encontraron registros de asistencia entre {start_date} y {end_date}.")
            else:
                headers = ["PIN", "Fecha", "Entrada", "Salida", "Minutos Trabajados", "Retardo", "Horas Extra", "Estado"]
                rows = []
                total_worked = 0
                total_tardiness = 0
                total_ot = 0
                absences = 0

                for r in filtered:
                    in_t = r.first_check_in.strftime("%H:%M:%S") if r.first_check_in else "--:--:--"
                    out_t = r.last_check_out.strftime("%H:%M:%S") if r.last_check_out else "--:--:--"
                    st_name = str(r.status.value if hasattr(r.status, "value") else r.status)

                    total_worked += r.total_worked_minutes
                    total_tardiness += r.tardiness_minutes
                    total_ot += r.overtime_minutes
                    if "ABSENT" in st_name.upper():
                        absences += 1

                    rows.append([
                        r.employee_pin,
                        str(r.date),
                        in_t,
                        out_t,
                        str(r.total_worked_minutes),
                        str(r.tardiness_minutes),
                        str(r.overtime_minutes),
                        st_name,
                    ])

                table_str = render_table(headers=headers, rows=rows, alignments=["left", "center", "center", "center", "right", "right", "right", "center"])
                summary_str = (
                    f"\n{bold('Resumen Consolidado:')}\n"
                    f"  • Total registros evaluados: {bold(str(len(filtered)))}\n"
                    f"  • Total horas trabajadas: {bold(f'{total_worked // 60}h {total_worked % 60}m')} ({total_worked} min)\n"
                    f"  • Total minutos retardo: {yellow(str(total_tardiness))}\n"
                    f"  • Total minutos horas extra: {cyan(str(total_ot))}\n"
                    f"  • Total inasistencias/faltas: {red(str(absences))}"
                )
                output_data = table_str + "\n" + summary_str

        # Manejo de destino de salida
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_data)
            print(f"{green('✔ Reporte guardado con éxito en:')} {bold(args.output)}")
        else:
            print(output_data)

        return 0

    except Exception as e:
        print(f"{red('✘ Error al generar reporte:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def register_report_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy report`."""
    rep_parser = subparsers.add_parser(
        "report",
        help="Generación y exportación de reportes de asistencia",
        description="Genera resúmenes de asistencia por período y empleado en formato tabla, CSV o JSON.",
    )
    rep_subparsers = rep_parser.add_subparsers(dest="report_action", required=True)

    # asistpy report summary
    summary_parser = rep_subparsers.add_parser(
        "summary",
        parents=[get_common_parser()],
        help="Genera resumen consolidado de asistencia",
        description="Calcula totales de tiempo trabajado, retardos, horas extras y ausencias en un rango.",
    )
    summary_parser.add_argument("--start-date", required=True, help="Fecha inicial del reporte (YYYY-MM-DD)")
    summary_parser.add_argument("--end-date", help="Fecha final del reporte (YYYY-MM-DD, por defecto igual a start-date)")
    summary_parser.add_argument("--employee-pin", help="Filtrar por PIN de empleado")
    summary_parser.add_argument(
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Formato de salida (table, csv, json; por defecto table)",
    )
    summary_parser.add_argument("--output", help="Ruta de archivo para guardar el reporte (ej. reporte.csv)")
    summary_parser.set_defaults(func=cmd_report_summary)

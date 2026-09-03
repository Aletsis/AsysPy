"""Comandos de administración y catálogo de empleados (`asistpy employee`)."""

import argparse
import sys
from datetime import date

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.organization.employee import Employee, Sex


def _parse_date(date_str: str) -> date:
    """Convierte una cadena YYYY-MM-DD a date."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido: '{date_str}'. Use YYYY-MM-DD.")


def cmd_employee_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo empleado en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)

    existing = bundle.employee_repo.get_by_pin(args.pin)
    if existing:
        print(f"{red('✘ Error:')} Ya existe un empleado registrado con el PIN '{args.pin}'.", file=sys.stderr)
        return 1

    hire_date = _parse_date(args.hire_date) if args.hire_date else date.today()
    sex = Sex(args.sex.lower()) if args.sex else Sex.MALE

    emp = Employee(
        id=None,
        pin=args.pin,
        first_name=args.first_name,
        paternal_last_name=args.paternal_last_name,
        maternal_last_name=args.maternal_last_name,
        hire_date=hire_date,
        sex=sex,
        department_id=args.department_id or 1,
        position=args.position or "General",
        home_branch_id=args.branch_id or 1,
        active=not args.inactive,
    )

    saved = bundle.employee_repo.save(emp)
    print(f"\n{green('✔')} Empleado {bold(saved.full_name)} (PIN: {saved.pin}) registrado exitosamente.")
    headers = ["ID", "PIN", "Nombre Completo", "Puesto", "Departamento", "Sucursal", "Fecha Ingreso", "Estado"]
    rows = [[
        str(saved.id or "-"),
        saved.pin,
        saved.full_name,
        saved.position,
        str(saved.department_id),
        str(saved.home_branch_id),
        saved.hire_date.isoformat(),
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "left", "right", "right", "center", "center"]))
    return 0


def cmd_employee_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un empleado."""
    bundle = ctx.get_bundle(init_tables=False)
    emp = bundle.employee_repo.get_by_pin(args.pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.pin}' no encontrado.", file=sys.stderr)
        return 1

    rows = [
        ["ID", str(emp.id or "-")],
        ["PIN / Identificador", emp.pin],
        ["Nombre Completo", emp.full_name],
        ["Nombre", emp.first_name],
        ["Apellido Paterno", emp.paternal_last_name],
        ["Apellido Materno", emp.maternal_last_name or "-"],
        ["Fecha de Contratación", emp.hire_date.isoformat()],
        ["Sexo", emp.sex.value],
        ["Puesto / Cargo", emp.position],
        ["Departamento ID", str(emp.department_id)],
        ["Sucursal Base ID", str(emp.home_branch_id)],
        ["Estado", green("Activo") if emp.active else red("Inactivo")],
    ]
    print(f"\n{cyan(bold('Detalle de Empleado:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_employee_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista los empleados registrados con filtros opcionales."""
    bundle = ctx.get_bundle(init_tables=False)

    if args.active_only:
        employees = bundle.employee_repo.list_active(branch_id=args.branch_id)
    else:
        employees = bundle.employee_repo.list_all(branch_id=args.branch_id)

    if args.pin:
        employees = [e for e in employees if args.pin in e.pin]

    if not employees:
        print(f"{yellow('No se encontraron empleados registrados con los criterios seleccionados.')}")
        return 0

    headers = ["ID", "PIN", "Nombre Completo", "Puesto", "Sucursal", "Fecha Ingreso", "Estado"]
    rows = []
    for e in employees:
        status_str = green("Activo") if e.active else red("Inactivo")
        rows.append([
            str(e.id or "-"),
            e.pin,
            e.full_name,
            e.position,
            str(e.home_branch_id),
            e.hire_date.isoformat(),
            status_str,
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "left", "right", "center", "center"],
    )
    print(table)
    print(f"\n{bold('Total empleados:')} {len(employees)}")
    return 0


def cmd_employee_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica la información de un empleado existente."""
    bundle = ctx.get_bundle(init_tables=True)
    emp = bundle.employee_repo.get_by_pin(args.pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.pin}' no encontrado.", file=sys.stderr)
        return 1

    if args.first_name is not None:
        emp.first_name = args.first_name
    if args.paternal_last_name is not None:
        emp.paternal_last_name = args.paternal_last_name
    if args.maternal_last_name is not None:
        emp.maternal_last_name = args.maternal_last_name
    if args.position is not None:
        emp.position = args.position
    if args.department_id is not None:
        emp.department_id = args.department_id
    if args.branch_id is not None:
        emp.home_branch_id = args.branch_id
    if args.active:
        emp.active = True
    elif args.inactive:
        emp.active = False

    saved = bundle.employee_repo.save(emp)
    print(f"\n{green('✔')} Empleado {bold(saved.full_name)} (PIN: {saved.pin}) actualizado exitosamente.")
    return 0


def cmd_employee_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un empleado del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    emp = bundle.employee_repo.get_by_pin(args.pin)
    if not emp:
        print(f"{red('✘ Error:')} Empleado con PIN '{args.pin}' no encontrado.", file=sys.stderr)
        return 1

    success = bundle.employee_repo.delete(args.pin)
    if success:
        print(f"\n{green('✔')} Empleado '{bold(emp.full_name)}' (PIN: {args.pin}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el empleado con PIN '{args.pin}'.", file=sys.stderr)
        return 1


def register_employee_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy employee`."""
    emp_parser = subparsers.add_parser(
        "employee",
        help="Gestión y catálogo CRUD de empleados",
        description="Permite dar de alta, consultar, actualizar y eliminar empleados de la organización.",
    )
    emp_subparsers = emp_parser.add_subparsers(dest="employee_action", required=True)

    # asistpy employee add
    add_parser = emp_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra un nuevo empleado",
    )
    add_parser.add_argument("--pin", required=True, help="PIN o identificador único del empleado (ej. 'E100')")
    add_parser.add_argument("--first-name", required=True, help="Nombre de pila del empleado")
    add_parser.add_argument("--paternal-last-name", required=True, help="Apellido paterno")
    add_parser.add_argument("--maternal-last-name", help="Apellido materno (opcional)")
    add_parser.add_argument("--hire-date", help="Fecha de ingreso YYYY-MM-DD (predeterminada: hoy)")
    add_parser.add_argument("--sex", choices=["male", "female"], default="male", help="Sexo (predeterminado: male)")
    add_parser.add_argument("--position", default="General", help="Cargo o puesto laboral")
    add_parser.add_argument("--department-id", type=int, default=1, help="ID de departamento (predeterminado: 1)")
    add_parser.add_argument("--branch-id", type=int, default=1, help="ID de sucursal base (predeterminado: 1)")
    add_parser.add_argument("--inactive", action="store_true", help="Registrar el empleado como inactivo")
    add_parser.set_defaults(func=cmd_employee_add)

    # asistpy employee show
    show_parser = emp_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un empleado",
    )
    show_parser.add_argument("--pin", required=True, help="PIN del empleado a consultar")
    show_parser.set_defaults(func=cmd_employee_show)

    # asistpy employee edit
    edit_parser = emp_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los datos de un empleado existente",
    )
    edit_parser.add_argument("--pin", required=True, help="PIN del empleado a modificar")
    edit_parser.add_argument("--first-name", help="Nuevo nombre de pila")
    edit_parser.add_argument("--paternal-last-name", help="Nuevo apellido paterno")
    edit_parser.add_argument("--maternal-last-name", help="Nuevo apellido materno")
    edit_parser.add_argument("--position", help="Nuevo cargo o puesto")
    edit_parser.add_argument("--department-id", type=int, help="Nuevo ID de departamento")
    edit_parser.add_argument("--branch-id", type=int, help="Nuevo ID de sucursal")
    status_group = edit_parser.add_mutually_exclusive_group()
    status_group.add_argument("--active", action="store_true", help="Marcar como activo")
    status_group.add_argument("--inactive", action="store_true", help="Marcar como inactivo")
    edit_parser.set_defaults(func=cmd_employee_edit)

    # asistpy employee delete
    del_parser = emp_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina un empleado del catálogo",
    )
    del_parser.add_argument("--pin", required=True, help="PIN del empleado a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_employee_delete)

    # asistpy employee list
    list_parser = emp_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los empleados registrados",
    )
    list_parser.add_argument("--branch-id", type=int, help="Filtrar por ID de sucursal")
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar solo empleados activos")
    list_parser.add_argument("--pin", help="Filtrar por coincidencia de PIN")
    list_parser.set_defaults(func=cmd_employee_list)

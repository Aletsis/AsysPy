"""Comandos de administración y catálogo de empleados (`asistpy employee`)."""

import argparse
import sys
from datetime import date

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.employee import Employee, Sex


def _parse_date(date_str: str) -> date:
    """Convierte una cadena YYYY-MM-DD a date."""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido: '{date_str}'. Use YYYY-MM-DD.")


def _find_employee(args: argparse.Namespace, bundle) -> Employee | None:
    """Busca un empleado por PIN o por ID interno."""
    if getattr(args, "pin", None):
        return bundle.employee_repo.get_by_pin(args.pin)
    if getattr(args, "employee_id", None) is not None:
        return bundle.employee_repo.get_by_id(args.employee_id)
    return None


def cmd_employee_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo empleado en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)

    existing = bundle.employee_repo.get_by_pin(args.pin)
    if existing:
        print(f"{red('✘ Error:')} Ya existe un empleado registrado con el PIN '{args.pin}'.", file=sys.stderr)
        return 1

    phone = args.phone if getattr(args, "phone", None) else getattr(args, "phone_number", None)
    hire_date = _parse_date(args.hire_date) if args.hire_date else date.today()
    sex = Sex(args.sex.lower()) if args.sex else Sex.MALE

    position_name = args.position or "General"
    if args.position_id and bundle.position_repo and (not args.position or args.position == "General"):
        pos_obj = bundle.position_repo.get_by_id(args.position_id)
        if pos_obj:
            position_name = pos_obj.name

    try:
        emp = Employee(
            id=None,
            pin=args.pin,
            first_name=args.first_name,
            paternal_last_name=args.paternal_last_name,
            maternal_last_name=args.maternal_last_name,
            hire_date=hire_date,
            sex=sex,
            department_id=args.department_id or 1,
            position_id=args.position_id,
            position=position_name,
            home_branch_id=args.branch_id or 1,
            active=not args.inactive,
            email=args.email,
            phone_number=phone,
            curp=args.curp,
            rfc=args.rfc,
            password=args.password,
            card_number=args.card_number,
        )
        saved = bundle.employee_repo.save(emp)
    except ValidationError as e:
        print(f"{red('✘ Error de validación:')} {e}", file=sys.stderr)
        return 1

    print(f"\n{green('✔')} Empleado {bold(saved.full_name)} (PIN: {saved.pin}) registrado exitosamente con ID {saved.id}.")
    headers = ["ID", "PIN", "Nombre Completo", "Puesto", "Depto ID", "Sucursal ID", "CURP", "Tarjeta", "Estado"]
    rows = [[
        str(saved.id or "-"),
        saved.pin,
        saved.full_name,
        f"{saved.position} (ID:{saved.position_id})" if saved.position_id else saved.position,
        str(saved.department_id),
        str(saved.home_branch_id),
        saved.curp or "-",
        saved.card_number or "-",
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "left", "center", "center", "left", "left", "center"],
    ))
    return 0


def cmd_employee_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un empleado."""
    bundle = ctx.get_bundle(init_tables=False)
    emp = _find_employee(args, bundle)
    if not emp:
        ident = getattr(args, "pin", None) or getattr(args, "employee_id", None)
        print(f"{red('✘ Error:')} Empleado '{ident}' no encontrado.", file=sys.stderr)
        return 1

    pwd_display = "********" if emp.password else "-"
    fingerprints_display = f"{len(emp.fingerprints)} registrada(s)" if emp.fingerprints else "0"

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
        ["Puesto ID", str(emp.position_id) if emp.position_id is not None else "-"],
        ["Departamento ID", str(emp.department_id)],
        ["Sucursal Base ID", str(emp.home_branch_id)],
        ["Correo Electrónico", emp.email or "-"],
        ["Teléfono", emp.phone_number or "-"],
        ["CURP", emp.curp or "-"],
        ["RFC", emp.rfc or "-"],
        ["Clave / Contraseña", pwd_display],
        ["Tarjeta RFID / Proximidad", emp.card_number or "-"],
        ["Huellas Biométricas", fingerprints_display],
        ["Estado", green("Activo") if emp.active else red("Inactivo")],
    ]
    print(f"\n{cyan(bold('Detalle de Empleado:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_employee_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista los empleados registrados con filtros opcionales."""
    bundle = ctx.get_bundle(init_tables=False)

    employees = bundle.employee_repo.list_all(
        branch_id=getattr(args, "branch_id", None),
        department_id=getattr(args, "department_id", None),
        position_id=getattr(args, "position_id", None),
        active_only=getattr(args, "active_only", False),
    )

    if args.pin:
        employees = [e for e in employees if args.pin in e.pin]

    if not employees:
        print(f"{yellow('No se encontraron empleados registrados con los criterios seleccionados.')}")
        return 0

    headers = ["ID", "PIN", "Nombre Completo", "Puesto", "Depto", "Sucursal", "Fecha Ingreso", "Estado"]
    rows = []
    for e in employees:
        status_str = green("Activo") if e.active else red("Inactivo")
        pos_str = f"{e.position} (#{e.position_id})" if e.position_id else e.position
        rows.append([
            str(e.id or "-"),
            e.pin,
            e.full_name,
            pos_str,
            str(e.department_id),
            str(e.home_branch_id),
            e.hire_date.isoformat(),
            status_str,
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "left", "center", "center", "center", "center"],
    )
    print(table)
    print(f"\n{bold('Total empleados:')} {len(employees)}")
    return 0


def cmd_employee_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica la información de un empleado existente."""
    bundle = ctx.get_bundle(init_tables=True)
    emp = _find_employee(args, bundle)
    if not emp:
        ident = getattr(args, "pin", None) or getattr(args, "employee_id", None)
        print(f"{red('✘ Error:')} Empleado '{ident}' no encontrado.", file=sys.stderr)
        return 1

    try:
        if args.first_name is not None:
            emp.first_name = args.first_name
        if args.paternal_last_name is not None:
            emp.paternal_last_name = args.paternal_last_name
        if args.maternal_last_name is not None:
            emp.maternal_last_name = args.maternal_last_name
        if args.position is not None:
            emp.position = args.position
        if args.position_id is not None:
            emp.position_id = args.position_id
            if bundle.position_repo and args.position is None:
                pos_obj = bundle.position_repo.get_by_id(args.position_id)
                if pos_obj:
                    emp.position = pos_obj.name
        if args.department_id is not None:
            emp.department_id = args.department_id
        if args.branch_id is not None:
            emp.home_branch_id = args.branch_id
        if args.email is not None:
            emp.email = args.email
        phone_val = getattr(args, "phone", None) or getattr(args, "phone_number", None)
        if phone_val is not None:
            emp.phone_number = phone_val
        if args.curp is not None:
            emp.curp = args.curp
        if args.rfc is not None:
            emp.rfc = args.rfc
        if args.password is not None:
            emp.password = args.password
        if args.card_number is not None:
            emp.card_number = args.card_number
        if getattr(args, "hire_date", None) is not None:
            emp.hire_date = _parse_date(args.hire_date)
        if getattr(args, "sex", None) is not None:
            emp.sex = Sex(args.sex.lower())
        if args.active:
            emp.active = True
        elif args.inactive:
            emp.active = False

        saved = bundle.employee_repo.save(emp)
    except ValidationError as err:
        print(f"{red('✘ Error de validación:')} {err}", file=sys.stderr)
        return 1

    print(f"\n{green('✔')} Empleado {bold(saved.full_name)} (PIN: {saved.pin}) actualizado exitosamente.")
    return 0


def cmd_employee_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un empleado del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    emp = _find_employee(args, bundle)
    if not emp:
        ident = getattr(args, "pin", None) or getattr(args, "employee_id", None)
        print(f"{red('✘ Error:')} Empleado '{ident}' no encontrado.", file=sys.stderr)
        return 1

    success = bundle.employee_repo.delete(emp.pin)
    if success:
        print(f"\n{green('✔')} Empleado '{bold(emp.full_name)}' (PIN: {emp.pin}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el empleado con PIN '{emp.pin}'.", file=sys.stderr)
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
    add_parser.add_argument("--position-id", type=int, help="ID de puesto laboral del catálogo de puestos")
    add_parser.add_argument("--department-id", type=int, default=1, help="ID de departamento (predeterminado: 1)")
    add_parser.add_argument("--branch-id", type=int, default=1, help="ID de sucursal base (predeterminado: 1)")
    add_parser.add_argument("--email", help="Correo electrónico de contacto del empleado")
    add_parser.add_argument("--phone", "--phone-number", dest="phone", help="Número telefónico de contacto")
    add_parser.add_argument("--curp", help="CURP del empleado (18 caracteres)")
    add_parser.add_argument("--rfc", help="RFC del empleado (12 o 13 caracteres)")
    add_parser.add_argument("--password", help="Contraseña o clave numérica de acceso en dispositivo")
    add_parser.add_argument("--card-number", help="Número de tarjeta de proximidad / RFID")
    add_parser.add_argument("--inactive", action="store_true", help="Registrar el empleado como inactivo")
    add_parser.set_defaults(func=cmd_employee_add)

    # asistpy employee show
    show_parser = emp_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un empleado",
    )
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument("--pin", help="PIN del empleado a consultar")
    show_group.add_argument("--employee-id", "--id", type=int, dest="employee_id", help="ID interno del empleado a consultar")
    show_parser.set_defaults(func=cmd_employee_show)

    # asistpy employee edit
    edit_parser = emp_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los datos de un empleado existente",
    )
    edit_ident = edit_parser.add_mutually_exclusive_group(required=True)
    edit_ident.add_argument("--pin", help="PIN del empleado a modificar")
    edit_ident.add_argument("--employee-id", "--id", type=int, dest="employee_id", help="ID interno del empleado a modificar")
    edit_parser.add_argument("--first-name", help="Nuevo nombre de pila")
    edit_parser.add_argument("--paternal-last-name", help="Nuevo apellido paterno")
    edit_parser.add_argument("--maternal-last-name", help="Nuevo apellido materno")
    edit_parser.add_argument("--position", help="Nuevo cargo o puesto")
    edit_parser.add_argument("--position-id", type=int, help="Nuevo ID de puesto del catálogo")
    edit_parser.add_argument("--department-id", type=int, help="Nuevo ID de departamento")
    edit_parser.add_argument("--branch-id", type=int, help="Nuevo ID de sucursal")
    edit_parser.add_argument("--email", help="Nuevo correo electrónico de contacto")
    edit_parser.add_argument("--phone", "--phone-number", dest="phone", help="Nuevo número telefónico")
    edit_parser.add_argument("--curp", help="Nueva CURP")
    edit_parser.add_argument("--rfc", help="Nuevo RFC")
    edit_parser.add_argument("--password", help="Nueva clave numérica o contraseña de dispositivo")
    edit_parser.add_argument("--card-number", help="Nuevo número de tarjeta de proximidad / RFID")
    edit_parser.add_argument("--hire-date", help="Nueva fecha de ingreso YYYY-MM-DD")
    edit_parser.add_argument("--sex", choices=["male", "female"], help="Nuevo sexo (male/female)")
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
    del_ident = del_parser.add_mutually_exclusive_group(required=True)
    del_ident.add_argument("--pin", help="PIN del empleado a eliminar")
    del_ident.add_argument("--employee-id", "--id", type=int, dest="employee_id", help="ID interno del empleado a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_employee_delete)

    # asistpy employee list
    list_parser = emp_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los empleados registrados",
    )
    list_parser.add_argument("--branch-id", type=int, help="Filtrar por ID de sucursal")
    list_parser.add_argument("--department-id", type=int, help="Filtrar por ID de departamento")
    list_parser.add_argument("--position-id", type=int, help="Filtrar por ID de puesto laboral")
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar solo empleados activos")
    list_parser.add_argument("--pin", help="Filtrar por coincidencia de PIN")
    list_parser.set_defaults(func=cmd_employee_list)

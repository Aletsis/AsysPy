"""Comandos de administración y catálogo de departamentos (`asistpy department`)."""

import argparse
import sys

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.organization.department import Department


def _find_department(args: argparse.Namespace, bundle) -> Department | None:
    """Busca un departamento por ID o por Código."""
    dept: Department | None = None
    if getattr(args, "department_id", None) is not None:
        dept = bundle.department_repo.get_by_id(args.department_id)
    elif getattr(args, "code", None):
        dept = bundle.department_repo.get_by_code(args.code)
    return dept


def cmd_department_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo departamento en la organización."""
    bundle = ctx.get_bundle(init_tables=True)

    if args.code:
        existing = bundle.department_repo.get_by_code(args.code)
        if existing:
            print(f"{red('✘ Error:')} Ya existe un departamento con el código '{args.code}' (ID: {existing.id}).", file=sys.stderr)
            return 1

    dept = Department(
        id=None,
        name=args.name,
        code=args.code,
        branch_id=args.branch_id,
        active=not args.inactive,
    )

    saved = bundle.department_repo.save(dept)
    print(f"\n{green('✔')} Departamento {bold(saved.name)} registrado exitosamente con ID {saved.id}.")
    headers = ["ID", "Código", "Nombre", "Sucursal ID", "Estado"]
    rows = [[
        str(saved.id or "-"),
        saved.code or "-",
        saved.name,
        str(saved.branch_id or "Todas"),
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "center", "center"]))
    return 0


def cmd_department_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un departamento."""
    bundle = ctx.get_bundle(init_tables=False)
    dept = _find_department(args, bundle)

    if not dept:
        ident = args.department_id if getattr(args, "department_id", None) else getattr(args, "code", "?")
        print(f"{red('✘ Error:')} Departamento '{ident}' no encontrado.", file=sys.stderr)
        return 1

    branch_name = "-"
    if dept.branch_id:
        branch = bundle.branch_repo.get_by_id(dept.branch_id)
        if branch:
            branch_name = f"{branch.name} ({branch.code})"

    positions = bundle.department_repo.get_positions(dept.id) if (dept.id and hasattr(bundle.department_repo, "get_positions")) else []
    positions_str = ", ".join(f"{p.name} (#{p.id})" for p in positions) if positions else "Ninguno asignado"

    rows = [
        ["ID", str(dept.id or "-")],
        ["Código", dept.code or "-"],
        ["Nombre", dept.name],
        ["Sucursal Asignada", branch_name if dept.branch_id else "Global (Todas las sucursales)"],
        ["Puestos Asociados", positions_str],
        ["Estado", green("Activo") if dept.active else red("Inactivo")],
    ]
    print(f"\n{cyan(bold('Detalle de Departamento:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_department_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista todos los departamentos registrados."""
    bundle = ctx.get_bundle(init_tables=False)
    depts = bundle.department_repo.list_all(
        branch_id=args.branch_id,
        active_only=args.active_only,
    )

    if not depts:
        print(f"{yellow('No se encontraron departamentos registrados con los criterios especificados.')}")
        return 0

    headers = ["ID", "Código", "Nombre", "Sucursal ID", "Estado"]
    rows = []
    for d in depts:
        rows.append([
            str(d.id or "-"),
            d.code or "-",
            d.name,
            str(d.branch_id or "Todas"),
            green("Activo") if d.active else red("Inactivo"),
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "center", "center"],
    )
    print(table)
    print(f"\n{bold('Total departamentos:')} {len(depts)}")
    return 0


def cmd_department_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica los datos de un departamento existente."""
    bundle = ctx.get_bundle(init_tables=True)
    dept = _find_department(args, bundle)

    if not dept:
        ident = args.department_id if getattr(args, "department_id", None) else getattr(args, "code", "?")
        print(f"{red('✘ Error:')} Departamento '{ident}' no encontrado.", file=sys.stderr)
        return 1

    if args.name is not None:
        dept.name = args.name
    if args.new_code is not None:
        dept.code = args.new_code
    if args.branch_id is not None:
        dept.branch_id = args.branch_id
    if args.active:
        dept.active = True
    elif args.inactive:
        dept.active = False

    saved = bundle.department_repo.save(dept)
    print(f"\n{green('✔')} Departamento {bold(saved.name)} (ID: {saved.id}) actualizado exitosamente.")
    return 0


def cmd_department_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un departamento del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    dept = _find_department(args, bundle)

    if not dept or dept.id is None:
        ident = args.department_id if getattr(args, "department_id", None) else getattr(args, "code", "?")
        print(f"{red('✘ Error:')} Departamento '{ident}' no encontrado.", file=sys.stderr)
        return 1

    success = bundle.department_repo.delete(dept.id)
    if success:
        print(f"\n{green('✔')} Departamento '{bold(dept.name)}' (ID: {dept.id}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el departamento con ID {dept.id}.", file=sys.stderr)
        return 1


def cmd_department_assign_position(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Asocia un puesto de trabajo a un departamento."""
    bundle = ctx.get_bundle(init_tables=True)
    dept = _find_department(args, bundle)
    if not dept or dept.id is None:
        ident = getattr(args, "department_id", None) or getattr(args, "code", "?")
        print(f"{red('✘ Error:')} Departamento '{ident}' no encontrado.", file=sys.stderr)
        return 1

    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El catálogo de puestos no está disponible.", file=sys.stderr)
        return 1

    pos = bundle.position_repo.get_by_id(args.position_id)
    if not pos:
        print(f"{red('✘ Error:')} Puesto con ID {args.position_id} no encontrado.", file=sys.stderr)
        return 1

    bundle.department_repo.assign_position(dept.id, args.position_id)
    print(f"\n{green('✔')} Puesto {bold(pos.name)} asignado al departamento {bold(dept.name)} exitosamente.")
    return 0


def cmd_department_remove_position(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Remueve la asociación entre un departamento y un puesto."""
    bundle = ctx.get_bundle(init_tables=True)
    dept = _find_department(args, bundle)
    if not dept or dept.id is None:
        ident = getattr(args, "department_id", None) or getattr(args, "code", "?")
        print(f"{red('✘ Error:')} Departamento '{ident}' no encontrado.", file=sys.stderr)
        return 1

    success = bundle.department_repo.remove_position(dept.id, args.position_id)
    if success:
        print(f"\n{green('✔')} Puesto #{args.position_id} desvinculado del departamento '{bold(dept.name)}' exitosamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se encontró la relación entre el departamento #{dept.id} y el puesto #{args.position_id}.", file=sys.stderr)
        return 1


def register_department_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy department`."""
    dept_parser = subparsers.add_parser(
        "department",
        help="Gestión y catálogo CRUD de departamentos",
        description="Permite registrar, listar, modificar y eliminar departamentos u áreas operativas.",
    )
    dept_subparsers = dept_parser.add_subparsers(dest="department_action", required=True)

    # asistpy department add
    add_parser = dept_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra un nuevo departamento",
    )
    add_parser.add_argument("--name", required=True, help="Nombre del departamento (ej. 'Recursos Humanos')")
    add_parser.add_argument("--code", help="Código único o clave del departamento (ej. 'RH-01')")
    add_parser.add_argument("--branch-id", type=int, help="ID de la sucursal a la que pertenece (opcional, default: global)")
    add_parser.add_argument("--inactive", action="store_true", help="Crear departamento en estado inactivo")
    add_parser.set_defaults(func=cmd_department_add)

    # asistpy department show
    show_parser = dept_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un departamento",
    )
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument("--department-id", type=int, help="ID del departamento a consultar")
    show_group.add_argument("--code", help="Código único del departamento a consultar")
    show_parser.set_defaults(func=cmd_department_show)

    # asistpy department edit
    edit_parser = dept_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los datos de un departamento existente",
    )
    edit_group = edit_parser.add_mutually_exclusive_group(required=True)
    edit_group.add_argument("--department-id", type=int, help="ID del departamento a modificar")
    edit_group.add_argument("--code", help="Código actual del departamento a modificar")
    edit_parser.add_argument("--name", help="Nuevo nombre del departamento")
    edit_parser.add_argument("--new-code", help="Nuevo código del departamento")
    edit_parser.add_argument("--branch-id", type=int, help="Nuevo ID de sucursal asignada")
    status_group = edit_parser.add_mutually_exclusive_group()
    status_group.add_argument("--active", action="store_true", help="Activar departamento")
    status_group.add_argument("--inactive", action="store_true", help="Desactivar departamento")
    edit_parser.set_defaults(func=cmd_department_edit)

    # asistpy department delete
    del_parser = dept_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina un departamento del catálogo",
    )
    del_group = del_parser.add_mutually_exclusive_group(required=True)
    del_group.add_argument("--department-id", type=int, help="ID del departamento a eliminar")
    del_group.add_argument("--code", help="Código del departamento a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_department_delete)

    # asistpy department list
    list_parser = dept_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los departamentos registrados",
    )
    list_parser.add_argument("--branch-id", type=int, help="Filtrar por ID de sucursal")
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar únicamente departamentos activos")
    list_parser.set_defaults(func=cmd_department_list)

    # asistpy department assign-position
    assign_pos = dept_subparsers.add_parser(
        "assign-position",
        parents=[get_common_parser()],
        help="Asocia un puesto de trabajo al departamento",
    )
    assign_group = assign_pos.add_mutually_exclusive_group(required=True)
    assign_group.add_argument("--department-id", type=int, help="ID del departamento")
    assign_group.add_argument("--code", help="Código del departamento")
    assign_pos.add_argument("--position-id", type=int, required=True, help="ID del puesto a asociar")
    assign_pos.set_defaults(func=cmd_department_assign_position)

    # asistpy department remove-position
    remove_pos = dept_subparsers.add_parser(
        "remove-position",
        parents=[get_common_parser()],
        help="Remueve la asociación de un puesto de trabajo del departamento",
    )
    remove_group = remove_pos.add_mutually_exclusive_group(required=True)
    remove_group.add_argument("--department-id", type=int, help="ID del departamento")
    remove_group.add_argument("--code", help="Código del departamento")
    remove_pos.add_argument("--position-id", type=int, required=True, help="ID del puesto a desvincular")
    remove_pos.set_defaults(func=cmd_department_remove_position)

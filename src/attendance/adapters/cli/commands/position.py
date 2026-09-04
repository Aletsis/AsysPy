"""Comandos de administración y catálogo de puestos (`asistpy position`)."""

import argparse
import sys

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.position import Position


def _find_position(args: argparse.Namespace, bundle) -> Position | None:
    """Busca un puesto por ID, Código o Nombre."""
    if not bundle.position_repo:
        return None
    pos_id = getattr(args, "position_id", None)
    if pos_id is not None:
        return bundle.position_repo.get_by_id(pos_id)
    code = getattr(args, "code", None)
    if code:
        return bundle.position_repo.get_by_code(code)
    name = getattr(args, "name", None)
    if name:
        return bundle.position_repo.get_by_name(name)
    return None


def cmd_position_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo puesto en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    if args.code and bundle.position_repo.exists_by_code(args.code):
        print(f"{red('✘ Error:')} Ya existe un puesto registrado con el código '{args.code}'.", file=sys.stderr)
        return 1

    try:
        pos = Position(
            id=None,
            name=args.name,
            code=args.code,
            description=args.description,
            active=not args.inactive,
        )
        saved = bundle.position_repo.save(pos)
    except ValidationError as e:
        print(f"{red('✘ Error de validación:')} {e}", file=sys.stderr)
        return 1

    print(f"\n{green('✔')} Puesto {bold(saved.name)} registrado exitosamente con ID {saved.id}.")
    headers = ["ID", "Código", "Nombre", "Descripción", "Estado"]
    rows = [[
        str(saved.id or "-"),
        saved.code or "-",
        saved.name,
        saved.description or "-",
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "left", "center"]))
    return 0


def cmd_position_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un puesto."""
    bundle = ctx.get_bundle(init_tables=False)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    pos = _find_position(args, bundle)
    if not pos:
        ident = getattr(args, "position_id", None) or getattr(args, "code", None) or getattr(args, "name", None)
        print(f"{red('✘ Error:')} Puesto '{ident}' no encontrado.", file=sys.stderr)
        return 1

    # Obtener departamentos asociados
    depts = bundle.position_repo.get_departments(pos.id) if pos.id else []
    depts_str = ", ".join(f"{d.name} (#{d.id})" for d in depts) if depts else "Ninguno asignado"

    rows = [
        ["ID", str(pos.id or "-")],
        ["Código", pos.code or "-"],
        ["Nombre", pos.name],
        ["Descripción", pos.description or "-"],
        ["Departamentos Asociados", depts_str],
        ["Estado", green("Activo") if pos.active else red("Inactivo")],
    ]
    print(f"\n{cyan(bold('Detalle de Puesto:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_position_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista los puestos registrados con filtros opcionales."""
    bundle = ctx.get_bundle(init_tables=False)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    positions = bundle.position_repo.list_all(
        department_id=getattr(args, "department_id", None),
        active_only=getattr(args, "active_only", False),
    )

    if not positions:
        print(f"{yellow('No se encontraron puestos registrados con los criterios seleccionados.')}")
        return 0

    headers = ["ID", "Código", "Nombre", "Descripción", "Estado"]
    rows = []
    for p in positions:
        status_str = green("Activo") if p.active else red("Inactivo")
        rows.append([
            str(p.id or "-"),
            p.code or "-",
            p.name,
            p.description or "-",
            status_str,
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "left", "center"],
    )
    print(table)
    print(f"\n{bold('Total puestos:')} {len(positions)}")
    return 0


def cmd_position_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica la información de un puesto existente."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    pos = _find_position(args, bundle)
    if not pos:
        ident = getattr(args, "position_id", None) or getattr(args, "code", None)
        print(f"{red('✘ Error:')} Puesto '{ident}' no encontrado.", file=sys.stderr)
        return 1

    try:
        if args.name is not None:
            pos.name = args.name
        if args.new_code is not None:
            pos.code = args.new_code
        if args.description is not None:
            pos.description = args.description
        if args.active:
            pos.active = True
        elif args.inactive:
            pos.active = False

        saved = bundle.position_repo.save(pos)
    except ValidationError as err:
        print(f"{red('✘ Error de validación:')} {err}", file=sys.stderr)
        return 1

    print(f"\n{green('✔')} Puesto {bold(saved.name)} (ID: {saved.id}) actualizado exitosamente.")
    return 0


def cmd_position_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un puesto del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    pos = _find_position(args, bundle)
    if not pos or pos.id is None:
        ident = getattr(args, "position_id", None) or getattr(args, "code", None)
        print(f"{red('✘ Error:')} Puesto '{ident}' no encontrado.", file=sys.stderr)
        return 1

    success = bundle.position_repo.delete(pos.id)
    if success:
        print(f"\n{green('✔')} Puesto '{bold(pos.name)}' (ID: {pos.id}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el puesto con ID {pos.id}.", file=sys.stderr)
        return 1


def cmd_position_assign_department(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Asocia un puesto a un departamento."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.position_repo or not bundle.department_repo:
        print(f"{red('✘ Error:')} Los repositorios requeridos no están disponibles.", file=sys.stderr)
        return 1

    pos = bundle.position_repo.get_by_id(args.position_id)
    if not pos:
        print(f"{red('✘ Error:')} Puesto con ID {args.position_id} no encontrado.", file=sys.stderr)
        return 1

    dept = bundle.department_repo.get_by_id(args.department_id)
    if not dept:
        print(f"{red('✘ Error:')} Departamento con ID {args.department_id} no encontrado.", file=sys.stderr)
        return 1

    bundle.position_repo.assign_department(args.position_id, args.department_id)
    print(f"\n{green('✔')} Puesto {bold(pos.name)} asignado al departamento {bold(dept.name)} exitosamente.")
    return 0


def cmd_position_remove_department(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Remueve la asociación entre un puesto y un departamento."""
    bundle = ctx.get_bundle(init_tables=True)
    if not bundle.position_repo:
        print(f"{red('✘ Error:')} El repositorio de puestos no está disponible.", file=sys.stderr)
        return 1

    success = bundle.position_repo.remove_department(args.position_id, args.department_id)
    if success:
        print(f"\n{green('✔')} Asociación entre puesto #{args.position_id} y departamento #{args.department_id} removida exitosamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se encontró la relación entre el puesto #{args.position_id} y el departamento #{args.department_id}.", file=sys.stderr)
        return 1


def register_position_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy position`."""
    pos_parser = subparsers.add_parser(
        "position",
        help="Gestión y catálogo CRUD de puestos laborales",
        description="Permite registrar, listar, modificar, eliminar y vincular puestos de trabajo en la organización.",
    )
    pos_subparsers = pos_parser.add_subparsers(dest="position_action", required=True)

    # asistpy position add
    add_parser = pos_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra un nuevo puesto de trabajo",
    )
    add_parser.add_argument("--name", required=True, help="Nombre del puesto (ej. 'Operador Especialista')")
    add_parser.add_argument("--code", help="Código único o clave del puesto (ej. 'PST-01')")
    add_parser.add_argument("--description", help="Descripción de las responsabilidades o funciones del puesto")
    add_parser.add_argument("--inactive", action="store_true", help="Crear puesto en estado inactivo")
    add_parser.set_defaults(func=cmd_position_add)

    # asistpy position show
    show_parser = pos_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un puesto",
    )
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument("--position-id", "--id", type=int, dest="position_id", help="ID del puesto a consultar")
    show_group.add_argument("--code", help="Código único del puesto a consultar")
    show_group.add_argument("--name", help="Nombre del puesto a consultar")
    show_parser.set_defaults(func=cmd_position_show)

    # asistpy position list
    list_parser = pos_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los puestos laborales registrados",
    )
    list_parser.add_argument("--department-id", type=int, help="Filtrar por ID de departamento asociado")
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar únicamente puestos activos")
    list_parser.set_defaults(func=cmd_position_list)

    # asistpy position edit
    edit_parser = pos_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los datos de un puesto existente",
    )
    edit_group = edit_parser.add_mutually_exclusive_group(required=True)
    edit_group.add_argument("--position-id", "--id", type=int, dest="position_id", help="ID del puesto a modificar")
    edit_group.add_argument("--code", help="Código actual del puesto a modificar")
    edit_parser.add_argument("--name", help="Nuevo nombre del puesto")
    edit_parser.add_argument("--new-code", help="Nuevo código del puesto")
    edit_parser.add_argument("--description", help="Nueva descripción del puesto")
    status_group = edit_parser.add_mutually_exclusive_group()
    status_group.add_argument("--active", action="store_true", help="Activar puesto")
    status_group.add_argument("--inactive", action="store_true", help="Desactivar puesto")
    edit_parser.set_defaults(func=cmd_position_edit)

    # asistpy position delete
    del_parser = pos_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina un puesto del catálogo",
    )
    del_group = del_parser.add_mutually_exclusive_group(required=True)
    del_group.add_argument("--position-id", "--id", type=int, dest="position_id", help="ID del puesto a eliminar")
    del_group.add_argument("--code", help="Código del puesto a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_position_delete)

    # asistpy position assign-department
    assign_parser = pos_subparsers.add_parser(
        "assign-department",
        parents=[get_common_parser()],
        help="Asocia un puesto a un departamento",
    )
    assign_parser.add_argument("--position-id", type=int, required=True, help="ID del puesto")
    assign_parser.add_argument("--department-id", type=int, required=True, help="ID del departamento")
    assign_parser.set_defaults(func=cmd_position_assign_department)

    # asistpy position remove-department
    remove_parser = pos_subparsers.add_parser(
        "remove-department",
        parents=[get_common_parser()],
        help="Remueve la asociación entre un puesto y un departamento",
    )
    remove_parser.add_argument("--position-id", type=int, required=True, help="ID del puesto")
    remove_parser.add_argument("--department-id", type=int, required=True, help="ID del departamento")
    remove_parser.set_defaults(func=cmd_position_remove_department)

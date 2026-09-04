"""Comandos de administración y catálogo de sucursales (`asistpy branch`)."""

import argparse
import sys

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.address import Address
from attendance.domain.organization.branch import Branch


def cmd_branch_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra una nueva sucursal en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)

    existing = bundle.branch_repo.get_by_code(args.code)
    if existing:
        print(f"{red('✘ Error:')} Ya existe una sucursal registrada con el código '{args.code}'.", file=sys.stderr)
        return 1

    address: Address | None = None
    if any([args.street, args.city, args.state, args.postal_code]):
        address = Address(
            street=args.street or "",
            exterior_number="",
            interior_number=None,
            postal_code=args.postal_code or "",
            neighborhood="",
            municipality=args.city or "",
            state=args.state or "",
        )

    try:
        branch = Branch(
            name=args.name,
            code=args.code,
            timezone=args.timezone or "America/Mexico_City",
            address=address,
            active=not args.inactive,
            email=args.email,
            phone_number=args.phone,
        )
        saved = bundle.branch_repo.save(branch)
    except ValidationError as e:
        print(f"{red('✘ Error de validación:')} {e}", file=sys.stderr)
        return 1
    print(f"\n{green('✔')} Sucursal {bold(saved.name)} (Código: {saved.code}) registrada exitosamente con ID {saved.id}.")
    headers = ["ID", "Código", "Nombre", "Zona Horaria", "Correo", "Teléfono", "Estado"]
    rows = [[
        str(saved.id or "-"),
        saved.code,
        saved.name,
        saved.timezone,
        saved.email or "-",
        saved.phone_number or "-",
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "left", "left", "left", "center"]))
    return 0


def cmd_branch_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de una sucursal."""
    bundle = ctx.get_bundle(init_tables=False)
    branch: Branch | None = None
    if args.branch_id is not None:
        branch = bundle.branch_repo.get_by_id(args.branch_id)
    elif args.code:
        branch = bundle.branch_repo.get_by_code(args.code)
    else:
        print(f"{red('✘ Error:')} Debe especificar --branch-id o --code para consultar la sucursal.", file=sys.stderr)
        return 1

    if not branch:
        print(f"{red('✘ Error:')} Sucursal no encontrada.", file=sys.stderr)
        return 1

    addr_str = f"{branch.address.municipality}, {branch.address.state}" if branch.address else "-"
    rows = [
        ["ID", str(branch.id or "-")],
        ["Código", branch.code],
        ["Nombre", branch.name],
        ["Zona Horaria", branch.timezone],
        ["Ubicación / Ciudad", addr_str],
        ["Correo Electrónico", branch.email or "-"],
        ["Teléfono", branch.phone_number or "-"],
        ["Estado", green("Activo") if branch.active else red("Inactivo")],
    ]
    print(f"\n{cyan(bold('Detalle de Sucursal:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_branch_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista las sucursales registradas."""
    bundle = ctx.get_bundle(init_tables=False)

    branches = bundle.branch_repo.list_all(active_only=args.active_only)

    if not branches:
        print(f"{yellow('No se encontraron sucursales registradas con los criterios seleccionados.')}")
        return 0

    headers = ["ID", "Código", "Nombre", "Zona Horaria", "Ciudad / Estado", "Estado"]
    rows = []
    for b in branches:
        status_str = green("Activo") if b.active else red("Inactivo")
        addr_str = f"{b.address.municipality}, {b.address.state}" if b.address else "-"
        rows.append([
            str(b.id or "-"),
            b.code,
            b.name,
            b.timezone,
            addr_str,
            status_str,
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "left", "left", "center"],
    )
    print(table)
    print(f"\n{bold('Total sucursales:')} {len(branches)}")
    return 0


def cmd_branch_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica los datos de una sucursal existente."""
    bundle = ctx.get_bundle(init_tables=True)
    branch: Branch | None = None
    if args.branch_id is not None:
        branch = bundle.branch_repo.get_by_id(args.branch_id)
    elif args.code:
        branch = bundle.branch_repo.get_by_code(args.code)
    else:
        print(f"{red('✘ Error:')} Debe especificar --branch-id o --code para modificar la sucursal.", file=sys.stderr)
        return 1

    if not branch:
        print(f"{red('✘ Error:')} Sucursal no encontrada.", file=sys.stderr)
        return 1

    try:
        if args.name is not None:
            branch.name = args.name
        if args.timezone is not None:
            branch.timezone = args.timezone
        if args.active:
            branch.active = True
        elif args.inactive:
            branch.active = False

        if args.email is not None:
            branch.email = args.email
        if args.phone is not None:
            branch.phone_number = args.phone

        if args.city or args.state or args.street or args.postal_code:
            curr = branch.address
            branch.address = Address(
                street=args.street or (curr.street if curr else ""),
                exterior_number=curr.exterior_number if curr else "",
                interior_number=curr.interior_number if curr else None,
                postal_code=args.postal_code or (curr.postal_code if curr else ""),
                neighborhood=curr.neighborhood if curr else "",
                municipality=args.city or (curr.municipality if curr else ""),
                state=args.state or (curr.state if curr else ""),
            )

        saved = bundle.branch_repo.save(branch)
    except ValidationError as err:
        print(f"{red('✘ Error de validación:')} {err}", file=sys.stderr)
        return 1

    print(f"\n{green('✔')} Sucursal {bold(saved.name)} (Código: {saved.code}) actualizada exitosamente.")
    return 0


def cmd_branch_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina una sucursal del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    branch: Branch | None = None
    if args.branch_id is not None:
        branch = bundle.branch_repo.get_by_id(args.branch_id)
    elif args.code:
        branch = bundle.branch_repo.get_by_code(args.code)
    else:
        print(f"{red('✘ Error:')} Debe especificar --branch-id o --code para eliminar la sucursal.", file=sys.stderr)
        return 1

    if not branch or branch.id is None:
        print(f"{red('✘ Error:')} Sucursal no encontrada.", file=sys.stderr)
        return 1

    success = bundle.branch_repo.delete(branch.id)
    if success:
        print(f"\n{green('✔')} Sucursal '{bold(branch.name)}' (ID: {branch.id}) eliminada correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar la sucursal con ID {branch.id}.", file=sys.stderr)
        return 1


def register_branch_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy branch`."""
    branch_parser = subparsers.add_parser(
        "branch",
        help="Gestión y catálogo CRUD de sucursales",
        description="Permite registrar, listar, modificar y eliminar sucursales de la empresa.",
    )
    branch_subparsers = branch_parser.add_subparsers(dest="branch_action", required=True)

    # asistpy branch add
    add_parser = branch_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra una nueva sucursal",
    )
    add_parser.add_argument("--name", required=True, help="Nombre de la sucursal (ej. 'Sucursal Matriz')")
    add_parser.add_argument("--code", required=True, help="Código único de la sucursal (ej. 'MAT-01')")
    add_parser.add_argument("--timezone", default="America/Mexico_City", help="Zona horaria IANA (predeterminado America/Mexico_City)")
    add_parser.add_argument("--email", help="Correo electrónico de contacto de la sucursal")
    add_parser.add_argument("--phone", help="Número telefónico de la sucursal")
    add_parser.add_argument("--city", help="Ciudad o alcaldía")
    add_parser.add_argument("--state", help="Estado o provincia")
    add_parser.add_argument("--street", help="Calle y número")
    add_parser.add_argument("--postal-code", help="Código postal")
    add_parser.add_argument("--inactive", action="store_true", help="Registrar como inactiva")
    add_parser.set_defaults(func=cmd_branch_add)

    # asistpy branch show
    show_parser = branch_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de una sucursal",
    )
    show_parser.add_argument("--branch-id", type=int, help="ID de la sucursal")
    show_parser.add_argument("--code", help="Código de la sucursal")
    show_parser.set_defaults(func=cmd_branch_show)

    # asistpy branch edit
    edit_parser = branch_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los datos de una sucursal existente",
    )
    edit_parser.add_argument("--branch-id", type=int, help="ID de la sucursal a modificar")
    edit_parser.add_argument("--code", help="Código de la sucursal a modificar")
    edit_parser.add_argument("--name", help="Nuevo nombre de la sucursal")
    edit_parser.add_argument("--timezone", help="Nueva zona horaria IANA")
    edit_parser.add_argument("--email", help="Nuevo correo electrónico de contacto")
    edit_parser.add_argument("--phone", help="Nuevo número telefónico de contacto")
    edit_parser.add_argument("--city", help="Nueva ciudad o alcaldía")
    edit_parser.add_argument("--state", help="Nuevo estado o provincia")
    edit_parser.add_argument("--street", help="Nueva calle")
    edit_parser.add_argument("--postal-code", help="Nuevo código postal")
    status_group = edit_parser.add_mutually_exclusive_group()
    status_group.add_argument("--active", action="store_true", help="Marcar como activa")
    status_group.add_argument("--inactive", action="store_true", help="Marcar como inactiva")
    edit_parser.set_defaults(func=cmd_branch_edit)

    # asistpy branch delete
    del_parser = branch_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina una sucursal del catálogo",
    )
    del_parser.add_argument("--branch-id", type=int, help="ID de la sucursal a eliminar")
    del_parser.add_argument("--code", help="Código de la sucursal a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_branch_delete)

    # asistpy branch list
    list_parser = branch_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista las sucursales registradas",
    )
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar solo sucursales activas")
    list_parser.set_defaults(func=cmd_branch_list)

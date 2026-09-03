"""Comandos de administración y diagnóstico de relojes biométricos (`asistpy device`)."""

import argparse
import os
import sys

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import bold, cyan, green, red, render_table, yellow
from attendance.adapters.zk_tcp.client import ZkTcpReader
from attendance.application.device.sync_all_active_devices import SyncAllActiveDevices
from attendance.application.device.sync_device_logs import sync_device_logs
from attendance.domain.device import Device, DeviceCapabilities, DeviceProtocol


def cmd_device_probe(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Prueba la conectividad y sondea información de hardware de un reloj biométrico."""
    bundle = ctx.get_bundle(init_tables=False)

    ip = args.ip
    port = args.port
    timeout = args.timeout or int(os.getenv("ZK_TIMEOUT", "60"))

    if args.device_id is not None:
        device = bundle.device_repo.get_by_id(args.device_id)
        if device is None:
            print(f"{red('✘ Error:')} Dispositivo con ID {args.device_id} no encontrado en catálogo.", file=sys.stderr)
            return 1
        ip = device.ip_address
        port = device.port
        print(f"Sondeando dispositivo '{bold(device.name)}' (ID: {device.id}) en {ip}:{port}...")
    else:
        ip = ip or os.getenv("ZK_DEVICE_IP", "192.168.0.233")
        port = port or int(os.getenv("ZK_DEVICE_PORT", "4370"))
        print(f"Sondeando dispositivo en {bold(ip)}:{bold(str(port))} (timeout={timeout}s)...")

    dummy_device = Device(
        id=args.device_id or 0,
        name="Sondeo CLI",
        ip_address=ip,
        port=port,
        branch_id=1,
    )

    reader = ZkTcpReader(timeout=timeout)
    try:
        reader.connect(dummy_device)
        try:
            info = reader.get_device_info(dummy_device)
            raw_logs = reader.get_raw_logs(dummy_device)
        finally:
            reader.disconnect()

        print(f"\n{green('✔ Conexión exitosa con el reloj biométrico.')}\n")
        rows = [
            ["Dirección IP", ip],
            ["Puerto TCP", str(port)],
            ["Versión Firmware", str(info.get("firmware", "Desconocida"))],
            ["Número de Serie", str(info.get("serial", "Desconocido"))],
            ["Marcaciones en Dispositivo", str(len(raw_logs))],
        ]
        table = render_table(
            headers=["Parámetro", "Valor"],
            rows=rows,
            alignments=["left", "left"],
        )
        print(table)
        return 0
    except Exception as e:
        print(f"{red('✘ Error durante el sondeo del dispositivo:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def cmd_device_sync(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Sincroniza marcaciones desde relojes biométricos activos hacia la base de datos."""
    bundle = ctx.get_bundle(init_tables=False)

    timeout = args.timeout or int(os.getenv("ZK_TIMEOUT", "60"))
    reader = ZkTcpReader(timeout=timeout)

    # Caso 1: Sincronizar un único dispositivo por ID
    if args.device_id is not None:
        device = bundle.device_repo.get_by_id(args.device_id)
        if device is None:
            print(f"{red('✘ Error:')} Dispositivo con ID {args.device_id} no encontrado en catálogo.", file=sys.stderr)
            return 1

        print(f"Sincronizando dispositivo '{bold(device.name)}' ({device.ip_address}:{device.port})...")
        try:
            count = sync_device_logs(
                device=device,
                reader=reader,
                attendance_repo=bundle.attendance_repo,
                sync_state_repo=bundle.sync_state_repo,
            )
            print(f"{green('✔ Sincronización finalizada.')} {bold(str(count))} nuevas marcaciones almacenadas.")
            return 0
        except Exception as e:
            print(f"{red('✘ Falló la sincronización:')} {e}", file=sys.stderr)
            if ctx.verbose:
                raise
            return 1

    # Caso 2: Sincronizar directamente por IP/Puerto
    if args.ip is not None:
        ip = args.ip
        port = args.port or int(os.getenv("ZK_DEVICE_PORT", "4370"))
        # Buscar si ya existe en catálogo
        existing = next((d for d in bundle.device_repo.list_all() if d.ip_address == ip and d.port == port), None)
        if existing is None:
            # Crear y registrar dispositivo transitorio
            existing = Device(
                id=None,
                name=f"Reloj {ip}",
                ip_address=ip,
                port=port,
                branch_id=1,
                active=True,
                capabilities=DeviceCapabilities(),
            )
            bundle.device_repo.save(existing)

        print(f"Sincronizando dispositivo en {bold(ip)}:{bold(str(port))} (ID asignado: {existing.id})...")
        try:
            count = sync_device_logs(
                device=existing,
                reader=reader,
                attendance_repo=bundle.attendance_repo,
                sync_state_repo=bundle.sync_state_repo,
            )
            print(f"{green('✔ Sincronización exitosa.')} {bold(str(count))} nuevas marcaciones almacenadas.")
            return 0
        except Exception as e:
            print(f"{red('✘ Falló la sincronización:')} {e}", file=sys.stderr)
            if ctx.verbose:
                raise
            return 1

    # Caso 3: Sincronización masiva de todos los dispositivos activos
    branch_id = args.branch_id
    stop_on_error = args.stop_on_error or os.getenv("SYNC_STOP_ON_ERROR", "false").lower() == "true"

    print("Iniciando sincronización masiva de dispositivos activos" + (f" en sucursal {branch_id}" if branch_id else "") + "...")

    orchestrator = SyncAllActiveDevices(
        device_registry=bundle.device_repo,
        attendance_repo=bundle.attendance_repo,
        sync_state_repo=bundle.sync_state_repo,
        reader=reader,
    )

    try:
        result = orchestrator.execute(branch_id=branch_id, stop_on_error=stop_on_error)

        headers = ["ID", "Nombre", "Estado", "Nuevas Marcaciones", "Detalle"]
        rows = []
        for r in result.results:
            status_str = green("OK") if r.success else red("FALLÓ")
            detail = r.error_message if r.error_message else "Completado"
            rows.append([
                str(r.device_id or "-"),
                r.device_name,
                status_str,
                str(r.synced_count),
                detail,
            ])

        print("\n" + render_table(headers=headers, rows=rows, alignments=["right", "left", "center", "right", "left"]))
        print(f"\n{bold('Resumen:')} Total: {result.total_devices} | Exitosos: {green(str(result.successful_devices))} | Fallidos: {red(str(result.failed_devices))} | Nuevas Marcaciones: {cyan(bold(str(result.total_synced_logs)))}")

        return 0 if result.failed_devices == 0 else 2
    except Exception as e:
        print(f"{red('✘ Error en orquestador de sincronización:')} {e}", file=sys.stderr)
        if ctx.verbose:
            raise
        return 1


def cmd_device_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Lista los dispositivos biométricos registrados en el catálogo."""
    bundle = ctx.get_bundle(init_tables=False)

    devices = bundle.device_repo.list_all()

    if args.branch_id is not None:
        devices = [d for d in devices if d.branch_id == args.branch_id]
    if args.active_only:
        devices = [d for d in devices if d.active]

    if not devices:
        print(f"{yellow('No se encontraron dispositivos registrados con los criterios seleccionados.')}")
        return 0

    headers = ["ID", "Nombre", "IP", "Puerto", "Sucursal", "Estado", "Último UID Sincronizado"]
    rows = []
    for d in devices:
        last_uid = bundle.sync_state_repo.get_last_synced_uid(d.id) if d.id is not None else 0
        status_str = green("Activo") if d.active else red("Inactivo")
        rows.append([
            str(d.id or "-"),
            d.name,
            d.ip_address,
            str(d.port),
            str(d.branch_id),
            status_str,
            str(last_uid),
        ])

    table = render_table(
        headers=headers,
        rows=rows,
        alignments=["right", "left", "left", "right", "right", "center", "right"],
    )
    print(table)
    print(f"\n{bold('Total dispositivos:')} {len(devices)}")
    return 0


def cmd_device_add(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Registra un nuevo dispositivo biométrico en el catálogo."""
    bundle = ctx.get_bundle(init_tables=True)

    protocol = DeviceProtocol(args.protocol) if args.protocol else DeviceProtocol.TCP_4370
    device = Device(
        name=args.name,
        ip_address=args.ip,
        port=args.port or 4370,
        branch_id=args.branch_id or 1,
        serial_number=args.serial or "",
        location_label=args.location,
        protocol=protocol,
        active=not args.inactive,
    )
    saved = bundle.device_repo.save(device)
    print(f"\n{green('✔')} Dispositivo registrado exitosamente con ID {bold(str(saved.id))}.")
    headers = ["ID", "Nombre", "IP", "Puerto", "Sucursal", "Serie", "Estado"]
    rows = [[
        str(saved.id),
        saved.name,
        saved.ip_address,
        str(saved.port),
        str(saved.branch_id),
        saved.serial_number or "-",
        green("Activo") if saved.active else red("Inactivo"),
    ]]
    print(render_table(headers=headers, rows=rows, alignments=["right", "left", "left", "right", "right", "left", "center"]))
    return 0


def cmd_device_show(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Muestra el detalle completo de un dispositivo biométrico."""
    bundle = ctx.get_bundle(init_tables=False)
    device = bundle.device_repo.get_by_id(args.device_id)
    if not device:
        print(f"{red('✘ Error:')} Dispositivo con ID {args.device_id} no encontrado.", file=sys.stderr)
        return 1

    last_uid = bundle.sync_state_repo.get_last_synced_uid(device.id) if device.id else 0
    rows: list[list[str]] = [
        ["ID", str(device.id)],
        ["Nombre", device.name],
        ["Dirección IP", device.ip_address or "-"],
        ["Puerto TCP", str(device.port)],
        ["Sucursal ID", str(device.branch_id)],
        ["Número de Serie", device.serial_number or "-"],
        ["Ubicación", device.location_label or "-"],
        ["Protocolo", device.protocol.value if device.protocol else "tcp_4370"],
        ["Estado", green("Activo") if device.active else red("Inactivo")],
        ["Último UID Sincronizado", str(last_uid)],
    ]
    print(f"\n{cyan(bold('Detalle del Dispositivo:'))}")
    print(render_table(headers=["Propiedad", "Valor"], rows=rows, alignments=["left", "left"]))
    return 0


def cmd_device_edit(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Modifica los datos de un dispositivo biométrico existente."""
    bundle = ctx.get_bundle(init_tables=True)
    device = bundle.device_repo.get_by_id(args.device_id)
    if not device:
        print(f"{red('✘ Error:')} Dispositivo con ID {args.device_id} no encontrado.", file=sys.stderr)
        return 1

    if args.name is not None:
        device.name = args.name
    if args.ip is not None:
        device.ip_address = args.ip
    if args.port is not None:
        device.port = args.port
    if args.branch_id is not None:
        device.branch_id = args.branch_id
    if args.serial is not None:
        device.serial_number = args.serial
    if args.location is not None:
        device.location_label = args.location
    if args.active:
        device.active = True
    elif args.inactive:
        device.active = False

    saved = bundle.device_repo.save(device)
    print(f"\n{green('✔')} Dispositivo {bold(str(saved.id))} actualizado exitosamente.")
    return 0


def cmd_device_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Elimina un dispositivo biométrico del catálogo."""
    bundle = ctx.get_bundle(init_tables=True)
    device = bundle.device_repo.get_by_id(args.device_id)
    if not device:
        print(f"{red('✘ Error:')} Dispositivo con ID {args.device_id} no encontrado.", file=sys.stderr)
        return 1

    success = bundle.device_repo.delete(args.device_id)
    if success:
        print(f"\n{green('✔')} Dispositivo '{bold(device.name)}' (ID: {args.device_id}) eliminado correctamente.")
        return 0
    else:
        print(f"{red('✘ Error:')} No se pudo eliminar el dispositivo con ID {args.device_id}.", file=sys.stderr)
        return 1


def register_device_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra los subcomandos de `asistpy device`."""
    dev_parser = subparsers.add_parser(
        "device",
        help="Diagnóstico, sincronización y catálogo CRUD de relojes biométricos",
        description="Permite administrar, sondear conectividad física y sincronizar relojes.",
    )
    dev_subparsers = dev_parser.add_subparsers(dest="device_action", required=True)

    # asistpy device add
    add_parser = dev_subparsers.add_parser(
        "add",
        parents=[get_common_parser()],
        help="Registra un nuevo reloj checador en el catálogo",
        description="Agrega un dispositivo biométrico con sus parámetros de red y sucursal.",
    )
    add_parser.add_argument("--name", required=True, help="Nombre identificador del reloj (ej. 'Reloj Entrada')")
    add_parser.add_argument("--ip", required=True, help="Dirección IP del reloj (ej. 192.168.1.200)")
    add_parser.add_argument("--port", type=int, default=4370, help="Puerto TCP (predeterminado 4370)")
    add_parser.add_argument("--branch-id", type=int, default=1, help="ID de la sucursal asignada (predeterminado 1)")
    add_parser.add_argument("--serial", default="", help="Número de serie del reloj")
    add_parser.add_argument("--location", help="Etiqueta de ubicación física")
    add_parser.add_argument("--protocol", default="tcp_4370", choices=["tcp_4370", "udp_4370"], help="Protocolo de comunicación")
    add_parser.add_argument("--inactive", action="store_true", help="Registrar el dispositivo como inactivo")
    add_parser.set_defaults(func=cmd_device_add)

    # asistpy device show
    show_parser = dev_subparsers.add_parser(
        "show",
        parents=[get_common_parser()],
        help="Muestra el detalle completo de un reloj checador",
    )
    show_parser.add_argument("--device-id", type=int, required=True, help="ID del dispositivo a consultar")
    show_parser.set_defaults(func=cmd_device_show)

    # asistpy device edit
    edit_parser = dev_subparsers.add_parser(
        "edit",
        parents=[get_common_parser()],
        help="Modifica los parámetros de un reloj checador registrado",
    )
    edit_parser.add_argument("--device-id", type=int, required=True, help="ID del dispositivo a modificar")
    edit_parser.add_argument("--name", help="Nuevo nombre identificador")
    edit_parser.add_argument("--ip", help="Nueva dirección IP")
    edit_parser.add_argument("--port", type=int, help="Nuevo puerto TCP")
    edit_parser.add_argument("--branch-id", type=int, help="Nuevo ID de sucursal")
    edit_parser.add_argument("--serial", help="Nuevo número de serie")
    edit_parser.add_argument("--location", help="Nueva ubicación física")
    status_group = edit_parser.add_mutually_exclusive_group()
    status_group.add_argument("--active", action="store_true", help="Marcar como activo")
    status_group.add_argument("--inactive", action="store_true", help="Marcar como inactivo")
    edit_parser.set_defaults(func=cmd_device_edit)

    # asistpy device delete
    del_parser = dev_subparsers.add_parser(
        "delete",
        parents=[get_common_parser()],
        help="Elimina un reloj checador del catálogo",
    )
    del_parser.add_argument("--device-id", type=int, required=True, help="ID del dispositivo a eliminar")
    del_parser.add_argument("--force", action="store_true", help="Confirmar eliminación sin confirmación interactiva")
    del_parser.set_defaults(func=cmd_device_delete)

    # asistpy device list
    list_parser = dev_subparsers.add_parser(
        "list",
        parents=[get_common_parser()],
        help="Lista los dispositivos registrados en el catálogo",
        description="Muestra los relojes biométricos guardados con sus IPs, estado y último UID.",
    )
    list_parser.add_argument("--branch-id", type=int, help="Filtrar por ID de sucursal")
    list_parser.add_argument("--active-only", action="store_true", help="Mostrar solo dispositivos activos")
    list_parser.set_defaults(func=cmd_device_list)

    # asistpy device probe
    probe_parser = dev_subparsers.add_parser(
        "probe",
        parents=[get_common_parser()],
        help="Sondea conectividad con un reloj biométrico ZKTeco",
        description="Realiza prueba de conexión TCP, consulta firmware y conteo de marcaciones.",
    )
    probe_parser.add_argument("--ip", help="Dirección IP del reloj (ej. 192.168.0.233)")
    probe_parser.add_argument("--port", type=int, help="Puerto TCP (predeterminado 4370)")
    probe_parser.add_argument("--timeout", type=int, help="Timeout de conexión en segundos")
    probe_parser.add_argument("--device-id", type=int, help="ID de dispositivo en catálogo")
    probe_parser.set_defaults(func=cmd_device_probe)

    # asistpy device sync
    sync_parser = dev_subparsers.add_parser(
        "sync",
        parents=[get_common_parser()],
        help="Sincroniza marcaciones desde relojes hacia la base de datos",
        description="Descarga e inserta nuevos registros de marcación cruda desde los dispositivos.",
    )
    sync_parser.add_argument("--device-id", type=int, help="ID de un dispositivo específico a sincronizar")
    sync_parser.add_argument("--ip", help="IP para sincronización directa sin registrar catálogo previo")
    sync_parser.add_argument("--port", type=int, help="Puerto TCP para sincronización directa")
    sync_parser.add_argument("--branch-id", type=int, help="Filtrar por sucursal")
    sync_parser.add_argument("--timeout", type=int, help="Timeout de conexión en segundos")
    sync_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Detener el proceso al encontrar un error en lugar de continuar con los demás",
    )
    sync_parser.set_defaults(func=cmd_device_sync)

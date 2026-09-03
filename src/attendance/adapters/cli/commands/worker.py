"""Comando CLI para el demonio/worker en segundo plano (`asistpy worker`)."""

import argparse
import os
import sys

from attendance.adapters.cli.context import CLIContext, get_common_parser
from attendance.adapters.cli.formatters import red, yellow
from attendance.application.worker.daemon import AttendanceWorker


def cmd_worker(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Ejecuta el demonio en segundo plano para sincronización continua y corte nocturno."""
    interval = args.interval
    if interval is None:
        interval = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))

    nightly_time = args.nightly_time or os.getenv("NIGHTLY_PROCESSING_TIME", "23:59")
    branch_id = args.branch_id
    if branch_id is None and os.getenv("SYNC_BRANCH_ID"):
        try:
            branch_id = int(os.getenv("SYNC_BRANCH_ID", ""))
        except ValueError:
            branch_id = None

    stop_on_error = args.stop_on_error or (os.getenv("SYNC_STOP_ON_ERROR", "false").lower() == "true")
    run_nightly_on_start = bool(args.run_nightly_on_start)
    once = bool(args.once)

    def get_bundle():
        return ctx.get_bundle(init_tables=False)

    worker = AttendanceWorker(
        get_bundle_fn=get_bundle,
        interval_seconds=interval,
        nightly_time=nightly_time,
        branch_id=branch_id,
        stop_on_error=stop_on_error,
        run_nightly_on_start=run_nightly_on_start,
        once=once,
    )

    try:
        return worker.start()
    except KeyboardInterrupt:
        print(f"\n{yellow('Worker detenido por el usuario.')}", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\n{red('✘ Error crítico en el worker:')} {exc}", file=sys.stderr)
        if ctx.verbose:
            import traceback

            traceback.print_exc()
        return 1


def register_worker_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Registra el subcomando 'worker' en la CLI de AsistPy."""
    parser = subparsers.add_parser(
        "worker",
        parents=[get_common_parser()],
        help="Ejecuta el demonio/worker en segundo plano 24/7 para sincronización periódica y corte nocturno.",
        description="Demonio en segundo plano desatendido para sincronización automática de relojes biométricos y evaluación diaria.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Intervalo en segundos entre ciclos de sincronización (default: 300 o variable SYNC_INTERVAL_SECONDS).",
    )
    parser.add_argument(
        "--nightly-time",
        type=str,
        default=None,
        help="Hora programada en formato HH:MM para el procesamiento nocturno de asistencia (default: 23:59 o variable NIGHTLY_PROCESSING_TIME).",
    )
    parser.add_argument(
        "--branch-id",
        type=int,
        default=None,
        help="Filtra la sincronización y corte únicamente para los relojes y personal de una sucursal específica.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        default=False,
        help="Detiene la ejecución del demonio ante cualquier excepción en lugar de registrarla y continuar.",
    )
    parser.add_argument(
        "--run-nightly-on-start",
        action="store_true",
        default=False,
        help="Ejecuta de inmediato el lote de corte diario al arrancar el worker, sin esperar a la hora programada.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Ejecuta una única ronda de sincronización y finaliza (útil para cron jobs o pruebas de diagnóstico).",
    )

    parser.set_defaults(func=cmd_worker)

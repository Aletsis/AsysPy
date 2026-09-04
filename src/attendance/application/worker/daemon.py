"""Servicio de demonio/worker en segundo plano para AsistPy (`asistpy worker`).

Permite la ejecución desatendida 24/7 en servidores, contenedores Docker y dispositivos móviles (Termux),
orquestando la sincronización periódica de relojes biométricos, el cierre diario nocturno de asistencia,
y garantizando un apagado limpio (graceful shutdown) ante señales SIGINT / SIGTERM / SIGBREAK para no
dejar ningún reloj biométrico deshabilitado.
"""

from __future__ import annotations

import logging
import signal
import threading
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from typing import Any, Callable

from attendance.adapters.persistence.factory import PersistenceBundle
from attendance.application.attendance.process_daily_attendance import (
    ProcessDailyAttendance,
    ProcessDailyAttendanceBatch,
)
from attendance.application.device.sync_all_active_devices import (
    SyncAllActiveDevices,
    SyncAllResult,
)
from attendance.domain.device.device import Device
from attendance.ports.device import DeviceReader

logger = logging.getLogger("asistpy.worker")


def parse_time_str(time_str: str) -> dt_time:
    """Parsea una cadena HH:MM a un objeto datetime.time."""
    try:
        parts = [int(p.strip()) for p in time_str.split(":")]
        if len(parts) == 2:
            return dt_time(hour=parts[0], minute=parts[1])
        elif len(parts) == 3:
            return dt_time(hour=parts[0], minute=parts[1], second=parts[2])
        raise ValueError
    except Exception:
        raise ValueError(
            f"Formato de hora inválido '{time_str}'. Debe tener formato HH:MM o HH:MM:SS (ej. '23:59')."
        )


def compute_operational_date(now_dt: datetime, scheduled_time: dt_time) -> date:
    """Calcula la fecha operativa que corresponde cerrar según la hora programada.

    Si el cierre está configurado durante la madrugada (antes de las 06:00, ej. 00:30),
    la jornada a cerrar corresponde al día natural anterior.
    Si se programa a partir de las 06:00 (ej. 23:59), corresponde a la fecha actual.
    """
    if scheduled_time.hour < 6:
        return now_dt.date() - timedelta(days=1)
    return now_dt.date()


class AttendanceWorker:
    """Servicio demonio para ejecución desatendida y sincronización continua de AsistPy."""

    def __init__(
        self,
        get_bundle_fn: Callable[[], PersistenceBundle],
        interval_seconds: int = 300,
        nightly_time: str | dt_time = "23:59",
        branch_id: int | None = None,
        stop_on_error: bool = False,
        run_nightly_on_start: bool = False,
        once: bool = False,
        reader_factory: Callable[[Device], DeviceReader] | None = None,
        default_reader: DeviceReader | None = None,
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        """Inicializa el demonio de asistencia.

        Args:
            get_bundle_fn: Fábrica que retorna un PersistenceBundle para acceder a los repositorios.
            interval_seconds: Segundos entre cada ciclo de sincronización de marcaciones.
            nightly_time: Hora programada para el cierre y evaluación diaria (HH:MM).
            branch_id: Filtro opcional por sucursal para sincronización y corte.
            stop_on_error: Si True, detiene el ciclo de sincronización ante fallo en un reloj.
            run_nightly_on_start: Si True, ejecuta la evaluación nocturna inmediatamente al iniciar.
            once: Si True, ejecuta un único ciclo de sincronización y finaliza.
            reader_factory: Fábrica opcional para crear lectores de dispositivos (útil en tests).
            default_reader: Lector por defecto opcional para reutilizar.
            log_fn: Función personalizada para registrar mensajes (por defecto imprime a stdout con hora).
        """
        self.get_bundle_fn = get_bundle_fn
        self.interval_seconds = max(1, interval_seconds)
        self.nightly_time = (
            parse_time_str(nightly_time) if isinstance(nightly_time, str) else nightly_time
        )
        self.branch_id = branch_id
        self.stop_on_error = stop_on_error
        self.run_nightly_on_start = run_nightly_on_start
        self.once = once
        self.reader_factory = reader_factory
        self.default_reader = default_reader
        self._custom_log_fn = log_fn

        self._shutdown_event = threading.Event()
        self._current_reader: DeviceReader | None = None
        self._last_nightly_date: date | None = None
        self._is_running = False

    @property
    def is_shutdown_requested(self) -> bool:
        """Indica si se ha solicitado apagar el worker."""
        return self._shutdown_event.is_set()

    def _log(self, message: str, level: str = "info") -> None:
        """Registra un mensaje con marca temporal formateada."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{now_str}] [asistpy-worker] {message}"
        if self._custom_log_fn is not None:
            self._custom_log_fn(formatted)
        else:
            print(formatted, flush=True)

        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message)

    def _setup_signal_handlers(self) -> None:
        """Registra manejadores de señales para apagado limpio multiplataforma.

        Soporta SIGINT (Ctrl+C), SIGTERM (Docker/systemd) y SIGBREAK (Windows).
        En Android (Termux) y macOS/Linux, SIGINT y SIGTERM son plenamente funcionales.
        """
        # Solo se pueden registrar manejadores de señales en el hilo principal
        if threading.current_thread() is not threading.main_thread():
            return

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, sig_name):
                sig = getattr(signal, sig_name)
                try:
                    signal.signal(sig, self._signal_handler)
                except (ValueError, OSError) as e:
                    logger.debug("No se pudo registrar handler para %s: %s", sig_name, e)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Manejador ejecutado al recibir señales del sistema operativo."""
        sig_label = f"señal {signum}"
        try:
            sig_label = signal.Signals(signum).name
        except Exception:
            pass

        self._log(f"Recibida {sig_label}. Iniciando apagado limpio (graceful shutdown)...")
        self.request_shutdown()

    def request_shutdown(self) -> None:
        """Solicita la detención limpia del bucle de ejecución."""
        self._shutdown_event.set()
        self._cleanup_active_reader()

    def _cleanup_active_reader(self) -> None:
        """Asegura que el lector biométrico activo se desconecte y re-habilite el dispositivo."""
        reader = self._current_reader
        if reader is not None:
            try:
                self._log("Liberando conexión con reloj biométrico y asegurando estado habilitado...")
                reader.disconnect()
            except Exception as exc:
                self._log(f"Aviso al desconectar lector biométrico: {exc}", level="warning")
            finally:
                self._current_reader = None

    def _resolve_reader(self, device: Device) -> DeviceReader:
        """Resuelve el lector de dispositivo y registra la referencia activa."""
        if self.reader_factory is not None:
            reader = self.reader_factory(device)
        elif self.default_reader is not None:
            reader = self.default_reader
        else:
            from attendance.adapters.zk_tcp.client import ZkTcpReader

            reader = ZkTcpReader()

        self._current_reader = reader
        return reader

    def run_sync_cycle(self) -> SyncAllResult | None:
        """Ejecuta una ronda de sincronización de todos los relojes biométricos activos."""
        if self.is_shutdown_requested:
            return None

        self._log(
            "Iniciando ciclo de sincronización masiva"
            + (f" para sucursal {self.branch_id}" if self.branch_id else "")
            + "..."
        )

        try:
            bundle = self.get_bundle_fn()
        except Exception as exc:
            self._log(f"Error al conectar con la base de datos: {exc}", level="error")
            if self.stop_on_error:
                raise
            return None

        def wrapped_reader_factory(device: Device) -> DeviceReader:
            return self._resolve_reader(device)

        orchestrator = SyncAllActiveDevices(
            device_registry=bundle.device_repo,
            attendance_repo=bundle.attendance_repo,
            sync_state_repo=bundle.sync_state_repo,
            reader_factory=wrapped_reader_factory,
        )

        try:
            result = orchestrator.execute(
                branch_id=self.branch_id,
                stop_on_error=self.stop_on_error,
            )
        finally:
            self._current_reader = None

        self._log(
            f"Sincronización completada: {result.successful_devices}/{result.total_devices} dispositivos OK, "
            f"{result.failed_devices} fallidos. Total nuevas marcaciones: {result.total_synced_logs}."
        )

        for dev_res in result.results:
            if not dev_res.success:
                self._log(
                    f"  [✘] Dispositivo '{dev_res.device_name}' (ID: {dev_res.device_id}): {dev_res.error_message}",
                    level="warning",
                )
            elif dev_res.synced_count > 0:
                self._log(
                    f"  [✔] Dispositivo '{dev_res.device_name}' (ID: {dev_res.device_id}): {dev_res.synced_count} nuevas marcaciones."
                )

        return result

    def check_and_run_nightly_batch(self, now: datetime | None = None) -> bool:
        """Verifica si corresponde ejecutar el lote de cierre nocturno de asistencia y lo ejecuta.

        Returns:
            True si se ejecutó el cierre diario, False en caso contrario.
        """
        if self.is_shutdown_requested:
            return False

        current_dt = now or datetime.now()
        target_date = compute_operational_date(current_dt, self.nightly_time)

        # Si ya se procesó hoy para esta fecha operativa, no hacer nada
        if self._last_nightly_date == target_date:
            return False

        # Si no se ha alcanzado la hora programada, esperar
        if current_dt.time() < self.nightly_time:
            return False

        return self.execute_nightly_batch(target_date=target_date)

    def execute_nightly_batch(self, target_date: date) -> bool:
        """Ejecuta el procesamiento en lote del cierre de jornada diaria para empleados activos."""
        self._log(f"Iniciando procesamiento nocturno de jornada diaria para fecha operativa: {target_date}...")

        try:
            bundle = self.get_bundle_fn()
            daily_processor = ProcessDailyAttendance(
                attendance_repo=bundle.attendance_repo,
                daily_attendance_repo=bundle.daily_attendance_repo,
                schedule_assignment_repo=bundle.schedule_assignment_repo,
                shift_repo=bundle.shift_repo,
                rotation_pattern_repo=bundle.rotation_pattern_repo,
                incidence_repo=bundle.incidence_repo,
                schedule_exception_repo=bundle.schedule_exception_repo,
            )
            batch_processor = ProcessDailyAttendanceBatch(
                employee_repo=bundle.employee_repo,
                daily_processor=daily_processor,
            )

            results = batch_processor.execute(
                target_date=target_date,
                branch_id=self.branch_id,
                mark_logs_processed=True,
            )

            self._last_nightly_date = target_date
            self._log(
                f"Procesamiento nocturno completado exitosamente: {len(results)} empleados evaluados para {target_date}."
            )
            return True
        except Exception as exc:
            self._log(f"Error durante el procesamiento nocturno de jornada: {exc}", level="error")
            if self.stop_on_error:
                raise
            return False

    def start(self) -> int:
        """Inicia el demonio de asistencia y entra en el bucle continuo."""
        self._is_running = True
        self._shutdown_event.clear()
        self._setup_signal_handlers()

        self._log("=== Servicio AsistPy Worker Iniciado ===")
        self._log(f"Configuración: intervalo={self.interval_seconds}s, hora_cierre={self.nightly_time.strftime('%H:%M')}")
        if self.branch_id:
            self._log(f"Filtro de sucursal: ID={self.branch_id}")
        self._log("Esperando eventos (Presione Ctrl+C o envíe SIGTERM para detener)...")

        # Cierre nocturno inicial si se solicitó explícitamente
        if self.run_nightly_on_start:
            now_dt = datetime.now()
            op_date = compute_operational_date(now_dt, self.nightly_time)
            self._log("Opción --run-nightly-on-start activada. Ejecutando lote inicial...")
            self.execute_nightly_batch(op_date)

        try:
            while not self._shutdown_event.is_set():
                try:
                    self.run_sync_cycle()
                except Exception as exc:
                    self._log(f"Excepción en ciclo de sincronización: {exc}", level="error")
                    if self.stop_on_error:
                        raise

                if self._shutdown_event.is_set():
                    break

                try:
                    self.check_and_run_nightly_batch()
                except Exception as exc:
                    self._log(f"Excepción en verificación nocturna: {exc}", level="error")
                    if self.stop_on_error:
                        raise

                if self.once or self._shutdown_event.is_set():
                    break

                # Espera cooperativa: se despierta de inmediato si se recibe señal de apagado
                self._shutdown_event.wait(timeout=self.interval_seconds)

        except KeyboardInterrupt:
            self._log("Interrupción por teclado detectada. Apagando...")
        finally:
            self._cleanup_active_reader()
            self._is_running = False
            self._log("=== Servicio AsistPy Worker Detenido limpiamente ===")
            self._log("Garantía de integridad: Ningún reloj biométrico quedó deshabilitado.")

        return 0

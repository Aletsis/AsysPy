"""Caso de uso orquestador SyncAllActiveDevices para sincronización masiva de dispositivos."""

from dataclasses import dataclass, field
from typing import Callable

from attendance.application.device.sync_device_logs import sync_device_logs
from attendance.domain.device.device import Device
from attendance.ports.attendance import AttendanceRepository
from attendance.ports.device import DeviceReader, DeviceRegistry, SyncStateRepository


@dataclass
class DeviceSyncResult:
    """Resultado individual de la sincronización de un reloj biométrico."""

    device_id: int | None
    device_name: str
    synced_count: int = 0
    success: bool = True
    error_message: str | None = None


@dataclass
class SyncAllResult:
    """Resumen consolidado de la sincronización de todos los dispositivos activos."""

    total_devices: int
    successful_devices: int
    failed_devices: int
    total_synced_logs: int
    results: list[DeviceSyncResult] = field(default_factory=list)


class SyncAllActiveDevices:
    """Orquestador para sincronizar de forma secuencial o por lote todos los dispositivos activos."""

    def __init__(
        self,
        device_registry: DeviceRegistry,
        attendance_repo: AttendanceRepository,
        sync_state_repo: SyncStateRepository,
        reader: DeviceReader | None = None,
        reader_factory: Callable[[Device], DeviceReader] | None = None,
        sync_device_logs_fn: Callable[..., int] = sync_device_logs,
    ) -> None:
        self.device_registry = device_registry
        self.attendance_repo = attendance_repo
        self.sync_state_repo = sync_state_repo
        self.reader = reader
        self.reader_factory = reader_factory
        self.sync_device_logs_fn = sync_device_logs_fn

    def _resolve_reader(self, device: Device) -> DeviceReader:
        if self.reader_factory is not None:
            return self.reader_factory(device)
        if self.reader is not None:
            return self.reader
        from attendance.adapters.zk_tcp.client import ZkTcpReader

        return ZkTcpReader()

    def execute(
        self,
        branch_id: int | None = None,
        stop_on_error: bool = False,
    ) -> SyncAllResult:
        """Ejecuta la sincronización sobre todos los dispositivos activos.

        Args:

            branch_id: Filtro opcional por sucursal.
            stop_on_error: Si es True, una excepción en un dispositivo detiene la ejecución.
                           Si es False (por defecto), se registra el fallo y se continúa con los demás.
        """
        try:
            active_devices = self.device_registry.get_active_devices(branch_id=branch_id)
        except TypeError:
            # Compatibilidad si una implementación externa de DeviceRegistry no acepta branch_id
            all_active = self.device_registry.get_active_devices()
            if branch_id is not None:
                active_devices = [d for d in all_active if d.branch_id == branch_id]
            else:
                active_devices = all_active

        results: list[DeviceSyncResult] = []
        total_synced_logs = 0
        successful_devices = 0
        failed_devices = 0

        for device in active_devices:
            try:
                device_reader = self._resolve_reader(device)
                count = self.sync_device_logs_fn(
                    device=device,
                    reader=device_reader,
                    attendance_repo=self.attendance_repo,
                    sync_state_repo=self.sync_state_repo,
                )
                successful_devices += 1
                total_synced_logs += count
                results.append(
                    DeviceSyncResult(
                        device_id=device.id,
                        device_name=device.name,
                        synced_count=count,
                        success=True,
                    )
                )
            except Exception as exc:
                failed_devices += 1
                results.append(
                    DeviceSyncResult(
                        device_id=device.id,
                        device_name=device.name,
                        synced_count=0,
                        success=False,
                        error_message=str(exc),
                    )
                )
                if stop_on_error:
                    raise

        return SyncAllResult(
            total_devices=len(active_devices),
            successful_devices=successful_devices,
            failed_devices=failed_devices,
            total_synced_logs=total_synced_logs,
            results=results,
        )

    def __call__(
        self,
        branch_id: int | None = None,
        stop_on_error: bool = False,
    ) -> SyncAllResult:
        return self.execute(branch_id=branch_id, stop_on_error=stop_on_error)


def sync_all_active_devices(
    device_registry: DeviceRegistry,
    attendance_repo: AttendanceRepository,
    sync_state_repo: SyncStateRepository,
    reader: DeviceReader | None = None,
    reader_factory: Callable[[Device], DeviceReader] | None = None,
    branch_id: int | None = None,
    stop_on_error: bool = False,
) -> SyncAllResult:
    """Función de conveniencia para orquestar la sincronización de todos los dispositivos activos."""
    orchestrator = SyncAllActiveDevices(
        device_registry=device_registry,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=reader,
        reader_factory=reader_factory,
    )
    return orchestrator.execute(branch_id=branch_id, stop_on_error=stop_on_error)

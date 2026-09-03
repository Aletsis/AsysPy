"""Workers asíncronos para operaciones de dispositivos biométricos en la GUI."""

import socket
from typing import Any

from PySide6.QtCore import QThread, Signal

from attendance.adapters.persistence.factory import PersistenceBundle
from attendance.domain.device.device import Device


class DeviceProbeWorker(QThread):
    """Prueba de conectividad TCP a un reloj biométrico en segundo plano."""

    finished_probe = Signal(bool, str, dict)  # (success, message, details)

    def __init__(self, ip: str, port: int = 4370, timeout: int = 5) -> None:
        super().__init__()
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def run(self) -> None:
        info: dict[str, Any] = {"ip": self.ip, "port": self.port}
        # 1. Prueba de socket TCP rápido
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, self.port))
            sock.close()
            info["socket_ok"] = True
        except Exception as e:
            self.finished_probe.emit(
                False,
                f"No se pudo establecer conexión TCP con {self.ip}:{self.port} ({e})",
                info,
            )
            return

        # 2. Intento de handshake con protocolo ZK si la librería pyzk está disponible
        try:
            from attendance.adapters.zk_tcp.client import ZkTcpReader
            temp_device = Device(
                id=None,
                name="Probe",
                ip_address=self.ip,
                port=self.port,
                active=True,
            )
            reader = ZkTcpReader(timeout=self.timeout)
            reader.connect(temp_device)
            try:
                device_info = reader.get_device_info(temp_device)
                info.update(device_info)
            finally:
                reader.disconnect()

            self.finished_probe.emit(
                True,
                f"Conexión exitosa con el reloj en {self.ip}:{self.port}",
                info,
            )
        except Exception as e:
            # Si el socket abrió pero el handshake de ZK falló, se reporta con advertencia
            self.finished_probe.emit(
                True,
                f"Puerto {self.port} abierto, pero el handshake ZK devolvió: {e}",
                info,
            )


class DeviceSyncWorker(QThread):
    """Sincroniza marcaciones de un dispositivo o de todos los activos sin congelar la UI."""

    progress = Signal(int, int, str)       # (actual, total, nombre_dispositivo)
    device_synced = Signal(int, str, int)  # (device_id, device_name, logs_count)
    finished_sync = Signal(bool, str, int) # (success, resumen, total_logs)
    error_occurred = Signal(str)           # mensaje de error

    def __init__(
        self,
        bundle: PersistenceBundle,
        device_id: int | None = None,
        branch_id: int | None = None,
    ) -> None:
        super().__init__()
        self.bundle = bundle
        self.device_id = device_id
        self.branch_id = branch_id

    def run(self) -> None:
        try:
            if self.device_id is not None:
                # Sincronización de un dispositivo específico
                device = self.bundle.device_repo.get_by_id(self.device_id)
                if not device:
                    self.error_occurred.emit(f"Dispositivo #{self.device_id} no encontrado.")
                    return

                self.progress.emit(1, 1, device.name)
                from attendance.adapters.zk_tcp.client import ZkTcpReader
                from attendance.application.device.sync_device_logs import sync_device_logs

                reader = ZkTcpReader()
                count = sync_device_logs(
                    device=device,
                    reader=reader,
                    attendance_repo=self.bundle.attendance_repo,
                    sync_state_repo=self.bundle.sync_state_repo,
                )
                self.device_synced.emit(device.id or 0, device.name, count)
                self.finished_sync.emit(
                    True,
                    f"Sincronizados {count} registros desde '{device.name}'.",
                    count,
                )
            else:
                # Sincronización masiva con SyncAllActiveDevices
                from attendance.adapters.zk_tcp.client import ZkTcpReader
                from attendance.application.device.sync_all_active_devices import (
                    SyncAllActiveDevices,
                )

                orchestrator = SyncAllActiveDevices(
                    device_registry=self.bundle.device_repo,
                    attendance_repo=self.bundle.attendance_repo,
                    sync_state_repo=self.bundle.sync_state_repo,
                    reader_factory=lambda dev: ZkTcpReader(),
                )

                result = orchestrator.execute(branch_id=self.branch_id, stop_on_error=False)
                for res in result.results:
                    if res.device_id:
                        self.device_synced.emit(res.device_id, res.device_name, res.synced_count)

                msg = (
                    f"Sincronización completa: {result.successful_devices}/{result.total_devices} "
                    f"dispositivos OK, {result.total_synced_logs} marcaciones nuevas."
                )
                self.finished_sync.emit(result.failed_devices == 0, msg, result.total_synced_logs)

        except Exception as e:
            self.error_occurred.emit(f"Error durante la sincronización: {e}")

"""Adapter que implementa el port DeviceReader usando pyzk (protocolo TCP 4370)."""

from zk import ZK
from zk.exception import ZKNetworkError

from attendance.domain.device import AttendanceLog, AuthMethod, Device, LogStatus
from attendance.ports.device import DeviceReader


class ZkTcpReader(DeviceReader):
    """Adapter que implementa el port DeviceReader usando pyzk (protocolo TCP 4370)."""

    def __init__(self, timeout: int = 60):
        self._timeout = timeout
        self._conn = None
        self._device_disable = False

    def connect(self, device: Device) -> None:
        zk = ZK(device.ip_address, port=device.port or 4370, timeout=self._timeout, ommit_ping=True)
        self._conn = zk.connect()

    def disconnect(self) -> None:
        if self._conn is None:
            return
        if self._device_disable:
            try:
                self._conn.enable_device()
            except ZKNetworkError:
                # No dejamos pasar esto en silencio: quien orqueste el sync
                # debe enterarse de que el reloj pudo quedar deshabilitado.
                raise
            finally:
                self._device_disable = False
        try:
            self._conn.disconnect()
        except ZKNetworkError:
            pass  # ya no hay conexión útil que cerrar

    def get_raw_logs(self, device: Device) -> list[AttendanceLog]:
        if self._conn is None:
            raise RuntimeError("Dispositivo no conectado.")
        self._conn.disable_device()
        self._device_disable = True
        try:
            records = self._conn.get_attendance()
            return [self._to_domain(r, device) for r in records]
        finally:
            self._conn.enable_device()
            self._device_disable = False

    def get_device_info(self, device: Device) -> dict:
        if self._conn is None:
            raise RuntimeError("Dispositivo no conectado.")
        return {
            "firmware": self._conn.get_firmware_version(),
            "serial": self._conn.get_serialnumber(),
        }

    def _to_domain(self, record, device: Device) -> AttendanceLog:
        return AttendanceLog(
            id=None,
            record_uid=record.uid if hasattr(record, "uid") else 0,
            employee_pin=str(record.user_id),
            device_id=device.id if device.id is not None else 0,
            timestamp=record.timestamp,

            raw_status=record.status,
            raw_punch=record.punch,
            auth_method=AuthMethod.from_punch_code(record.punch),
            processing_status=LogStatus.RAW,
            inferred_type=None,
        )

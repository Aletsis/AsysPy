"""Puerto DeviceReader para lectura de relojes biométricos."""

from typing import Protocol

from attendance.domain.device.device import Device
from attendance.domain.device.log import AttendanceLog


class DeviceReader(Protocol):
    """Contrato para leer datos de un reloj, sin importar el protocolo."""

    def connect(self, device: Device) -> None: ...
    def disconnect(self) -> None: ...
    def get_raw_logs(self, device: Device) -> list[AttendanceLog]: ...
    def get_device_info(self, device: Device) -> dict: ...

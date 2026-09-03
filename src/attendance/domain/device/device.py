"""Entidad Device y DeviceCapabilities."""

from dataclasses import dataclass
from datetime import datetime

from attendance.domain.common.exceptions import ValidationError

from .enums import DeviceProtocol


@dataclass
class DeviceCapabilities:
    """Metadatos de diagnóstico y hardware reportados por el dispositivo biométrico."""

    firmware_version: str | None = None
    platform: str | None = None
    manufacturer_device_name: str | None = None
    face_algorithm_version: str | None = None
    fingerprint_algorithm_version: str | None = None
    mac_address: str | None = None
    pin_width: int | None = None
    last_read_at: datetime | None = None


@dataclass
class Device:
    """Reloj checador / dispositivo biométrico registrado."""

    id: int | None = None
    name: str = ""
    branch_id: int = 0
    protocol: DeviceProtocol | None = DeviceProtocol.TCP_4370
    serial_number: str = ""
    ip_address: str | None = None
    port: int | None = 4370
    location_label: str | None = None
    capabilities: DeviceCapabilities | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValidationError("El nombre del dispositivo no puede estar vacío.")
        if self.port is not None and (self.port < 1 or self.port > 65535):
            raise ValidationError("El puerto de red debe estar entre 1 y 65535.")


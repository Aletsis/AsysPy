"""Entidad Device y DeviceCapabilities."""

from dataclasses import dataclass
from datetime import datetime

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

    id: int
    name: str
    branch_id: int
    protocol: DeviceProtocol | None = DeviceProtocol.TCP_4370
    serial_number: str = ""
    ip_address: str | None = None
    port: int | None = 4370
    location_label: str | None = None
    capabilities: DeviceCapabilities | None = None
    active: bool = True

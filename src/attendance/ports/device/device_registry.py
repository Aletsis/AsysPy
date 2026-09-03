"""Puerto DeviceRegistry para catálogo de dispositivos."""

from typing import Protocol

from attendance.domain.device.device import Device


class DeviceRegistry(Protocol):
    """De donde salen los dispositivos a consultar (DB o configuración estática)."""

    def get_active_devices(self, branch_id: int | None = None) -> list[Device]: ...


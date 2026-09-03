"""Puerto DeviceRepository para catálogo y persistencia de dispositivos biométricos."""

from typing import Protocol

from attendance.domain.device.device import Device


class DeviceRepository(Protocol):
    """Contrato de persistencia y catálogo para dispositivos biométricos."""

    def save(self, device: Device) -> Device: ...

    def get_by_id(self, device_id: int) -> Device | None: ...

    def get_by_serial_number(self, serial_number: str) -> Device | None: ...

    def get_active_devices(self, branch_id: int | None = None) -> list[Device]: ...

    def list_all(self, branch_id: int | None = None) -> list[Device]: ...

    def delete(self, device_id: int) -> bool: ...

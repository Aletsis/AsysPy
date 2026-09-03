"""Adaptador en memoria para DeviceRepository y DeviceRegistry."""

from typing import Dict

from attendance.domain.device.device import Device
from attendance.ports.device.device_registry import DeviceRegistry
from attendance.ports.device.device_repository import DeviceRepository


class InMemoryDeviceRepository(DeviceRepository, DeviceRegistry):
    """Implementación en memoria para el catálogo de dispositivos biométricos."""

    def __init__(self, initial_devices: list[Device] | None = None) -> None:
        self._by_id: Dict[int, Device] = {}
        self._by_serial: Dict[str, Device] = {}
        self._next_id = 1
        if initial_devices:
            for dev in initial_devices:
                self.save(dev)

    def save(self, device: Device) -> Device:
        if device.id is None:
            device.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, device.id + 1)

        self._by_id[device.id] = device
        if device.serial_number:
            self._by_serial[device.serial_number] = device
        return device

    def get_by_id(self, device_id: int) -> Device | None:
        return self._by_id.get(device_id)

    def get_by_serial_number(self, serial_number: str) -> Device | None:
        if not serial_number:
            return None
        return self._by_serial.get(serial_number)

    def get_active_devices(self, branch_id: int | None = None) -> list[Device]:
        devices = [d for d in self._by_id.values() if d.active]
        if branch_id is not None:
            devices = [d for d in devices if d.branch_id == branch_id]
        return devices

    def list_all(self, branch_id: int | None = None) -> list[Device]:
        devices = list(self._by_id.values())
        if branch_id is not None:
            devices = [d for d in devices if d.branch_id == branch_id]
        return devices

    def delete(self, device_id: int) -> bool:
        if device_id in self._by_id:
            device = self._by_id.pop(device_id)
            if device.serial_number and device.serial_number in self._by_serial:
                del self._by_serial[device.serial_number]
            return True
        return False

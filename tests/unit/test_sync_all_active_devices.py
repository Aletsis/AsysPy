"""Pruebas unitarias para el caso de uso orquestador SyncAllActiveDevices."""

from datetime import datetime

import pytest

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryDeviceRepository,
    InMemorySyncStateRepository,
)
from attendance.application.device import (
    SyncAllActiveDevices,
    sync_all_active_devices,
)
from attendance.domain.device import AttendanceLog, AuthMethod, Device, LogStatus


class FakeDeviceReader:
    def __init__(self, logs_by_device_id: dict[int, list[AttendanceLog]] | None = None) -> None:
        self.logs_by_device_id = logs_by_device_id or {}
        self.connected_devices: list[int] = []
        self.disconnected = False

    def connect(self, device: Device) -> None:
        if device.id in self.logs_by_device_id and self.logs_by_device_id[device.id] is None:
            raise ConnectionError(f"No se pudo conectar al dispositivo {device.name}")
        if device.id is not None:
            self.connected_devices.append(device.id)

    def disconnect(self) -> None:
        self.disconnected = True

    def get_raw_logs(self, device: Device) -> list[AttendanceLog]:
        return self.logs_by_device_id.get(device.id or 0, [])

    def get_device_info(self, device: Device) -> dict:
        return {}


def make_log(uid: int, device_id: int, pin: str = "EMP01") -> AttendanceLog:
    return AttendanceLog(
        id=None,
        record_uid=uid,
        employee_pin=pin,
        device_id=device_id,
        timestamp=datetime(2026, 3, 1, 8, 0, 0),
        raw_status=1,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )


def test_sync_all_active_devices_successfully() -> None:
    # 1. Preparar repositorio de dispositivos
    dev1 = Device(id=1, name="Reloj Entrada", branch_id=1, ip_address="10.0.0.1", active=True)
    dev2 = Device(id=2, name="Reloj Salida", branch_id=1, ip_address="10.0.0.2", active=True)
    dev3 = Device(id=3, name="Reloj Inactivo", branch_id=1, ip_address="10.0.0.3", active=False)

    device_repo = InMemoryDeviceRepository([dev1, dev2, dev3])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    reader = FakeDeviceReader({
        1: [make_log(1, 1), make_log(2, 1)],
        2: [make_log(1, 2), make_log(2, 2), make_log(3, 2)],
    })

    orchestrator = SyncAllActiveDevices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=reader,
    )

    result = orchestrator.execute()

    assert result.total_devices == 2
    assert result.successful_devices == 2
    assert result.failed_devices == 0
    assert result.total_synced_logs == 5

    # Verificar detalles por dispositivo
    assert len(result.results) == 2
    assert result.results[0].device_id == 1
    assert result.results[0].synced_count == 2
    assert result.results[0].success is True

    assert result.results[1].device_id == 2
    assert result.results[1].synced_count == 3
    assert result.results[1].success is True

    # Verificar persistencia en repositorios
    assert len(attendance_repo.get_unprocessed_logs()) == 5
    assert sync_state_repo.get_last_synced_uid(1) == 2
    assert sync_state_repo.get_last_synced_uid(2) == 3


def test_sync_all_active_devices_branch_filter() -> None:
    dev1 = Device(id=1, name="Reloj Sucursal 1", branch_id=10, active=True)
    dev2 = Device(id=2, name="Reloj Sucursal 2", branch_id=20, active=True)

    device_repo = InMemoryDeviceRepository([dev1, dev2])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    reader = FakeDeviceReader({
        1: [make_log(1, 1)],
        2: [make_log(1, 2)],
    })

    orchestrator = SyncAllActiveDevices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=reader,
    )

    # Solo sincronizar sucursal 10
    result = orchestrator.execute(branch_id=10)

    assert result.total_devices == 1
    assert result.successful_devices == 1
    assert result.total_synced_logs == 1
    assert result.results[0].device_id == 1
    assert sync_state_repo.get_last_synced_uid(1) == 1
    assert sync_state_repo.get_last_synced_uid(2) == 0  # no se tocó


def test_sync_all_active_devices_fault_tolerance() -> None:
    dev1 = Device(id=1, name="Reloj Bueno", branch_id=1, active=True)
    dev2 = Device(id=2, name="Reloj Dañado", branch_id=1, active=True)
    dev3 = Device(id=3, name="Reloj Otro Bueno", branch_id=1, active=True)

    device_repo = InMemoryDeviceRepository([dev1, dev2, dev3])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    # None en logs_by_device_id simula fallo de red en connect
    reader = FakeDeviceReader({
        1: [make_log(1, 1)],
        2: None,  # provoca ConnectionError
        3: [make_log(1, 3), make_log(2, 3)],
    })

    orchestrator = SyncAllActiveDevices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=reader,
    )

    # Con stop_on_error=False (default): no explota, registra fallo y continúa con el reloj 3
    result = orchestrator.execute(stop_on_error=False)

    assert result.total_devices == 3
    assert result.successful_devices == 2
    assert result.failed_devices == 1
    assert result.total_synced_logs == 3

    assert result.results[0].success is True
    assert result.results[0].synced_count == 1

    assert result.results[1].success is False
    assert result.results[1].synced_count == 0
    assert "No se pudo conectar al dispositivo Reloj Dañado" in (result.results[1].error_message or "")

    assert result.results[2].success is True
    assert result.results[2].synced_count == 2


def test_sync_all_active_devices_stop_on_error_raises() -> None:
    dev1 = Device(id=1, name="Reloj Con Falla", branch_id=1, active=True)

    device_repo = InMemoryDeviceRepository([dev1])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    reader = FakeDeviceReader({1: None})

    orchestrator = SyncAllActiveDevices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=reader,
    )

    with pytest.raises(ConnectionError, match="No se pudo conectar"):
        orchestrator.execute(stop_on_error=True)


def test_sync_all_active_devices_with_reader_factory() -> None:
    dev = Device(id=10, name="Reloj con Factory", branch_id=1, active=True)
    device_repo = InMemoryDeviceRepository([dev])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    created_readers: list[Device] = []

    def factory(device: Device) -> FakeDeviceReader:
        created_readers.append(device)
        return FakeDeviceReader({device.id: [make_log(1, device.id or 0)]})

    result = sync_all_active_devices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader_factory=factory,
    )

    assert len(created_readers) == 1
    assert created_readers[0].name == "Reloj con Factory"
    assert result.total_synced_logs == 1
    assert result.successful_devices == 1


def test_sync_all_active_devices_no_active_devices() -> None:
    device_repo = InMemoryDeviceRepository([])
    attendance_repo = InMemoryAttendanceRepository()
    sync_state_repo = InMemorySyncStateRepository()

    result = sync_all_active_devices(
        device_registry=device_repo,
        attendance_repo=attendance_repo,
        sync_state_repo=sync_state_repo,
        reader=FakeDeviceReader(),
    )

    assert result.total_devices == 0
    assert result.successful_devices == 0
    assert result.failed_devices == 0
    assert result.total_synced_logs == 0
    assert len(result.results) == 0

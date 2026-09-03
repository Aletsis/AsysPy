from datetime import datetime

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemorySyncStateRepository,
)
from attendance.application.device import sync_device_logs
from attendance.domain.device import AttendanceLog, AuthMethod, Device, LogStatus


class FakeDeviceReader:
    def __init__(self, logs: list[AttendanceLog]):
        self._logs = logs
        self.connected = False

    def connect(self, device):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def get_raw_logs(self, device):
        return self._logs

    def get_device_info(self, device):
        return {}


class FakeAttendanceRepository(InMemoryAttendanceRepository):
    def __init__(self):
        super().__init__()
        self.saved: list[AttendanceLog] = []

    def save_raw_log(self, log: AttendanceLog) -> None:
        super().save_raw_log(log)
        self.saved.append(log)


class FakeSyncStateRepository(InMemorySyncStateRepository):
    def __init__(self, initial_uid: int = 0):
        super().__init__({1: initial_uid})
        self.updated_to: int | None = None

    def update_last_synced_uid(self, device_id: int, uid: int) -> None:
        super().update_last_synced_uid(device_id, uid)
        self.updated_to = uid


def make_log(uid: int) -> AttendanceLog:
    return AttendanceLog(
        id=None,
        record_uid=uid,
        employee_pin="1965",
        device_id=1,
        timestamp=datetime(2026, 1, 1),
        raw_status=3,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )


def test_first_sync_brings_all_logs():
    device = Device(
        id=1, name="Reloj A", ip_address="10.0.0.1", port=4370, protocol=None, branch_id=1
    )
    logs = [make_log(1), make_log(2), make_log(3)]
    reader = FakeDeviceReader(logs)
    attendance_repo = FakeAttendanceRepository()
    sync_state_repo = FakeSyncStateRepository(initial_uid=0)

    count = sync_device_logs(device, reader, attendance_repo, sync_state_repo)

    assert count == 3
    assert len(attendance_repo.saved) == 3
    assert sync_state_repo.updated_to == 3


def test_only_new_logs_are_synced():
    device = Device(
        id=1, name="Reloj A", ip_address="10.0.0.1", port=4370, protocol=None, branch_id=1
    )
    logs = [make_log(1), make_log(2), make_log(3)]
    reader = FakeDeviceReader(logs)
    attendance_repo = FakeAttendanceRepository()
    sync_state_repo = FakeSyncStateRepository(initial_uid=2)  # ya sincronizamos hasta el 2

    count = sync_device_logs(device, reader, attendance_repo, sync_state_repo)

    assert count == 1
    assert attendance_repo.saved[0].record_uid == 3


def test_no_new_logs_returns_zero():
    device = Device(
        id=1, name="Reloj A", ip_address="10.0.0.1", port=4370, protocol=None, branch_id=1
    )
    reader = FakeDeviceReader([make_log(1), make_log(2)])
    attendance_repo = FakeAttendanceRepository()
    sync_state_repo = FakeSyncStateRepository(initial_uid=2)

    count = sync_device_logs(device, reader, attendance_repo, sync_state_repo)

    assert count == 0
    assert sync_state_repo.updated_to is None  # no debe actualizar si no hubo nada nuevo


def test_device_reset_resyncs_everything():
    device = Device(
        id=1, name="Reloj A", ip_address="10.0.0.1", port=4370, protocol=None, branch_id=1
    )
    # el dispositivo fue limpiado: ahora trae uids bajos aunque ya habíamos sincronizado hasta el 100
    reader = FakeDeviceReader([make_log(1), make_log(2)])
    attendance_repo = FakeAttendanceRepository()
    sync_state_repo = FakeSyncStateRepository(initial_uid=100)

    count = sync_device_logs(device, reader, attendance_repo, sync_state_repo)

    assert count == 2  # se resincronizó todo, no se descartó por ser menor al watermark

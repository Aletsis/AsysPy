"""Caso de uso para sincronizar marcaciones crudas desde dispositivos biométricos."""

from attendance.domain.device.device import Device
from attendance.ports.attendance import AttendanceRepository
from attendance.ports.device import DeviceReader, SyncStateRepository


def sync_device_logs(
    device: Device,
    reader: DeviceReader,
    attendance_repo: AttendanceRepository,
    sync_state_repo: SyncStateRepository,
) -> int:
    last_synced_uid = sync_state_repo.get_last_synced_uid(device.id)

    reader.connect(device)
    try:
        all_logs = reader.get_raw_logs(device)
    finally:
        reader.disconnect()

    if all_logs and max(log.record_uid for log in all_logs) < last_synced_uid:
        # el dispositivo fue reseteado/limpiado - resincroniza todo
        last_synced_uid = 0
        new_logs = all_logs
    else:
        new_logs = [log for log in all_logs if log.record_uid > last_synced_uid]

    if not new_logs:
        return 0

    for log in new_logs:
        attendance_repo.save_raw_log(log)

    newest_uid = max(log.record_uid for log in new_logs)
    sync_state_repo.update_last_synced_uid(device.id, newest_uid)

    return len(new_logs)

"""Adaptador en memoria para SyncStateRepository."""

from typing import Dict

from attendance.ports.device import SyncStateRepository


class InMemorySyncStateRepository(SyncStateRepository):
    """Implementación en memoria para el control de marcas de agua de sincronización."""

    def __init__(self, initial_states: dict[int, int] | None = None) -> None:
        self._states: Dict[int, int] = dict(initial_states or {})

    def get_last_synced_uid(self, device_id: int) -> int:
        return self._states.get(device_id, 0)

    def update_last_synced_uid(self, device_id: int, last_synced_uid: int) -> None:
        self._states[device_id] = last_synced_uid

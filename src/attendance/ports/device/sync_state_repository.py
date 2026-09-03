"""Puerto SyncStateRepository para control de marcas de agua de sincronización."""

from typing import Protocol


class SyncStateRepository(Protocol):
    """Contrato de persistencia para el estado de sincronización con dispositivos biométricos."""

    def get_last_synced_uid(self, device_id: int) -> int: ...

    def update_last_synced_uid(self, device_id: int, last_synced_uid: int) -> None: ...

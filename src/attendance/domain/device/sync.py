"""Entidad SyncState para control de sincronización con dispositivos."""

from dataclasses import dataclass


@dataclass
class SyncState:
    """Estado de marca de agua (watermark) de sincronización de un dispositivo."""

    device_id: int
    last_synced_uid: int = 0

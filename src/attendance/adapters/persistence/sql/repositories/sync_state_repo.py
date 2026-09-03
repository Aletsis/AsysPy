"""Adaptador SQLAlchemy para SyncStateRepository (Marcas de agua de sincronización)."""

from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.models import SyncStateModel
from attendance.ports.device import SyncStateRepository


class SqlSyncStateRepository(SyncStateRepository):
    """Implementación relacional del repositorio de marcas de agua para biométricos."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def get_last_synced_uid(self, device_id: int) -> int:
        with self.session_factory() as session:
            model = session.get(SyncStateModel, device_id)
            return model.last_synced_uid if model else 0

    def update_last_synced_uid(self, device_id: int, last_synced_uid: int) -> None:
        with self.session_factory() as session:
            model = session.get(SyncStateModel, device_id)
            if model is not None:
                model.last_synced_uid = last_synced_uid
            else:
                model = SyncStateModel(device_id=device_id, last_synced_uid=last_synced_uid)
                session.add(model)
            session.commit()

"""Adaptador SQLAlchemy para DeviceRepository y DeviceRegistry."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    capabilities_to_dict,
    device_to_domain,
    device_to_model,
)
from attendance.adapters.persistence.sql.models import DeviceModel
from attendance.domain.device.device import Device
from attendance.domain.device.enums import DeviceProtocol
from attendance.ports.device.device_registry import DeviceRegistry
from attendance.ports.device.device_repository import DeviceRepository


class SqlDeviceRepository(DeviceRepository, DeviceRegistry):
    """Implementación relacional del repositorio de dispositivos biométricos."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, device: Device) -> Device:
        with self.session_factory() as session:
            existing: DeviceModel | None = None
            if device.id is not None:
                existing = session.get(DeviceModel, device.id)
            if existing is None and device.serial_number:
                stmt = select(DeviceModel).where(DeviceModel.serial_number == device.serial_number)
                existing = session.scalars(stmt).first()

            if existing is not None:
                existing.name = device.name
                existing.branch_id = device.branch_id
                existing.protocol = (
                    device.protocol.value if device.protocol else DeviceProtocol.TCP_4370.value
                )
                existing.serial_number = device.serial_number or ""
                existing.ip_address = device.ip_address
                existing.port = device.port
                existing.location_label = device.location_label
                existing.capabilities = capabilities_to_dict(device.capabilities)
                existing.active = device.active
                session.commit()
                device.id = existing.id
                return device_to_domain(existing)
            else:
                model = device_to_model(device)
                session.add(model)
                session.commit()
                device.id = model.id
                return device_to_domain(model)

    def get_by_id(self, device_id: int) -> Device | None:
        with self.session_factory() as session:
            model = session.get(DeviceModel, device_id)
            return device_to_domain(model) if model else None

    def get_by_serial_number(self, serial_number: str) -> Device | None:
        if not serial_number:
            return None
        with self.session_factory() as session:
            stmt = select(DeviceModel).where(DeviceModel.serial_number == serial_number)
            model = session.scalars(stmt).first()
            return device_to_domain(model) if model else None

    def get_active_devices(self, branch_id: int | None = None) -> list[Device]:
        with self.session_factory() as session:
            stmt = select(DeviceModel).where(DeviceModel.active.is_(True))
            if branch_id is not None:
                stmt = stmt.where(DeviceModel.branch_id == branch_id)
            stmt = stmt.order_by(DeviceModel.name.asc(), DeviceModel.id.asc())
            models = session.scalars(stmt).all()
            return [device_to_domain(m) for m in models]

    def list_all(self, branch_id: int | None = None) -> list[Device]:
        with self.session_factory() as session:
            stmt = select(DeviceModel)
            if branch_id is not None:
                stmt = stmt.where(DeviceModel.branch_id == branch_id)
            stmt = stmt.order_by(DeviceModel.name.asc(), DeviceModel.id.asc())
            models = session.scalars(stmt).all()
            return [device_to_domain(m) for m in models]

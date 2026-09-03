"""Pruebas unitarias para la entidad Device y el adaptador InMemoryDeviceRepository."""

from datetime import datetime

import pytest

from attendance.adapters.memory.in_memory_device_repo import InMemoryDeviceRepository
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.device.device import Device, DeviceCapabilities
from attendance.domain.device.enums import DeviceProtocol


def test_device_creation_and_validation() -> None:
    # Creación válida
    dev = Device(
        id=None,
        name="Reloj Entrada Principal",
        branch_id=1,
        ip_address="192.168.1.50",
        port=4370,
        protocol=DeviceProtocol.TCP_4370,
        serial_number="ZK12345678",
    )
    assert dev.id is None
    assert dev.name == "Reloj Entrada Principal"
    assert dev.active is True
    assert dev.port == 4370

    # Nombre vacío debe fallar
    with pytest.raises(ValidationError, match="nombre del dispositivo no puede estar vacío"):
        Device(id=1, name="", branch_id=1)

    # Puerto inválido menor a 1 debe fallar
    with pytest.raises(ValidationError, match="puerto de red debe estar entre 1 y 65535"):
        Device(id=1, name="Reloj 1", branch_id=1, port=0)

    # Puerto inválido mayor a 65535 debe fallar
    with pytest.raises(ValidationError, match="puerto de red debe estar entre 1 y 65535"):
        Device(id=1, name="Reloj 1", branch_id=1, port=70000)


def test_device_capabilities_metadata() -> None:
    now = datetime(2026, 3, 1, 10, 0, 0)
    caps = DeviceCapabilities(
        firmware_version="Ver 6.60 Nov 15 2020",
        platform="ZEM560",
        manufacturer_device_name="iClock 360",

        face_algorithm_version="v12.0",
        fingerprint_algorithm_version="v10.0",
        mac_address="00:17:61:12:34:56",
        pin_width=9,
        last_read_at=now,
    )
    dev = Device(
        id=1,
        name="Reloj Biomátrico Facial",
        branch_id=2,
        capabilities=caps,
    )
    assert dev.capabilities is not None
    assert dev.capabilities.firmware_version == "Ver 6.60 Nov 15 2020"
    assert dev.capabilities.last_read_at == now


def test_in_memory_device_repository_crud() -> None:
    repo = InMemoryDeviceRepository()

    # 1. Guardar nuevo dispositivo (autogenera ID)
    dev1 = Device(
        id=None,
        name="Reloj Norte",
        branch_id=10,
        ip_address="192.168.1.101",
        serial_number="SN-001",
        active=True,
    )
    saved1 = repo.save(dev1)
    assert saved1.id == 1

    # 2. Guardar segundo dispositivo
    dev2 = Device(
        id=None,
        name="Reloj Sur",
        branch_id=20,
        ip_address="192.168.1.102",
        serial_number="SN-002",
        active=False,
    )
    saved2 = repo.save(dev2)
    assert saved2.id == 2

    # 3. Consultas por ID y por Serial Number
    by_id = repo.get_by_id(1)
    assert by_id is not None
    assert by_id.name == "Reloj Norte"

    by_serial = repo.get_by_serial_number("SN-002")
    assert by_serial is not None
    assert by_serial.id == 2

    assert repo.get_by_id(999) is None
    assert repo.get_by_serial_number("INEXISTENTE") is None
    assert repo.get_by_serial_number("") is None

    # 4. Listar activos
    active_all = repo.get_active_devices()
    assert len(active_all) == 1
    assert active_all[0].id == 1

    # 5. Filtrar por sucursal
    active_b10 = repo.get_active_devices(branch_id=10)
    assert len(active_b10) == 1
    active_b20 = repo.get_active_devices(branch_id=20)
    assert len(active_b20) == 0  # está inactivo

    # 6. Listar todos
    all_devs = repo.list_all()
    assert len(all_devs) == 2

    all_b20 = repo.list_all(branch_id=20)
    assert len(all_b20) == 1
    assert all_b20[0].id == 2

    # 7. Actualizar dispositivo existente
    saved1.name = "Reloj Norte Actualizado"
    saved1.active = False
    repo.save(saved1)

    updated = repo.get_by_id(1)
    assert updated is not None
    assert updated.name == "Reloj Norte Actualizado"
    assert updated.active is False
    assert len(repo.get_active_devices()) == 0

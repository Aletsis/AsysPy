"""Pruebas unitarias para el servicio demonio AttendanceWorker y apagado limpio."""

import threading
from datetime import date, datetime
from datetime import time as dt_time
from unittest.mock import MagicMock

import pytest

from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.application.worker.daemon import (
    AttendanceWorker,
    compute_operational_date,
    parse_time_str,
)
from attendance.domain.device.device import Device
from attendance.domain.organization.employee import Employee, Sex


@pytest.fixture
def mock_bundle():
    """Genera un PersistenceBundle en memoria con datos de prueba."""
    bundle = PersistenceFactory.create_bundle("memory")

    # Añadir dispositivo activo
    device = Device(
        id=1,
        name="Reloj Entrada",
        ip_address="192.168.1.201",
        port=4370,
        branch_id=1,
        active=True,
    )
    bundle.device_repo.save(device)

    # Añadir empleado
    emp = Employee(
        id=1,
        pin="1001",
        first_name="Juan",
        paternal_last_name="Perez",
        maternal_last_name=None,
        hire_date=date(2024, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        position="Operador",
        home_branch_id=1,
        active=True,
    )
    bundle.employee_repo.save(emp)

    return bundle


def test_parse_time_str():
    assert parse_time_str("23:59") == dt_time(23, 59)
    assert parse_time_str("00:30") == dt_time(0, 30)
    assert parse_time_str("08:15:30") == dt_time(8, 15, 30)
    with pytest.raises(ValueError):
        parse_time_str("invalid")


def test_compute_operational_date():
    dt_day = datetime(2026, 9, 3, 23, 59)
    # Si hora programada es 23:59, la fecha operativa es hoy
    assert compute_operational_date(dt_day, dt_time(23, 59)) == date(2026, 9, 3)

    # Si hora programada es en la madrugada (ej. 01:00 AM del 4 de sept), corresponde al 3 de sept
    dt_dawn = datetime(2026, 9, 4, 1, 0)
    assert compute_operational_date(dt_dawn, dt_time(1, 0)) == date(2026, 9, 3)


def test_worker_sync_cycle(mock_bundle):
    mock_reader = MagicMock()
    mock_reader.get_raw_logs.return_value = []

    logs = []
    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=10,
        default_reader=mock_reader,
        log_fn=logs.append,
    )

    result = worker.run_sync_cycle()

    assert result is not None
    assert result.total_devices == 1
    assert result.successful_devices == 1
    assert mock_reader.connect.called
    assert mock_reader.disconnect.called


def test_worker_sync_cycle_device_error(mock_bundle):
    failing_reader = MagicMock()
    failing_reader.connect.side_effect = ConnectionError("No se pudo conectar al reloj")

    logs = []
    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=10,
        default_reader=failing_reader,
        stop_on_error=False,
        log_fn=logs.append,
    )

    result = worker.run_sync_cycle()

    assert result is not None
    assert result.total_devices == 1
    assert result.successful_devices == 0
    assert result.failed_devices == 1
    assert any("No se pudo conectar al reloj" in msg for msg in logs)


def test_worker_nightly_batch_trigger(mock_bundle):
    logs = []
    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=10,
        nightly_time="23:00",
        log_fn=logs.append,
    )

    # Simular hora previa a las 23:00 (ej. 22:45) -> No debe ejecutarse
    before_time = datetime(2026, 9, 3, 22, 45)
    executed_before = worker.check_and_run_nightly_batch(now=before_time)
    assert executed_before is False

    # Simular hora igual o posterior a las 23:00 (ej. 23:05) -> Debe ejecutarse
    at_time = datetime(2026, 9, 3, 23, 5)
    executed_at = worker.check_and_run_nightly_batch(now=at_time)
    assert executed_at is True
    assert worker._last_nightly_date == date(2026, 9, 3)

    # Segundo llamado en el mismo día no debe re-ejecutar
    executed_again = worker.check_and_run_nightly_batch(now=datetime(2026, 9, 3, 23, 30))
    assert executed_again is False


def test_worker_graceful_shutdown_cooperative_wait(mock_bundle):
    """Verifica que request_shutdown interrumpe la espera de forma inmediata sin demoras."""
    mock_reader = MagicMock()
    mock_reader.get_raw_logs.return_value = []

    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=300,  # 5 minutos
        default_reader=mock_reader,
        once=False,
    )

    # Detener el worker después de 0.1 segundos desde un hilo secundario
    def stopper():
        import time
        time.sleep(0.05)
        worker.request_shutdown()

    stop_thread = threading.Thread(target=stopper)
    stop_thread.start()

    start_t = datetime.now()
    ret = worker.start()
    duration = (datetime.now() - start_t).total_seconds()

    stop_thread.join()
    assert ret == 0
    # Debe haber terminado en menos de 2 segundos a pesar del intervalo de 300s
    assert duration < 2.0
    assert worker.is_shutdown_requested is True


def test_worker_graceful_shutdown_cleans_active_reader(mock_bundle):
    """Verifica que si se apaga mientras hay un reader activo, se garantiza su desconexión."""
    mock_reader = MagicMock()

    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=10,
        default_reader=mock_reader,
    )

    worker._current_reader = mock_reader
    worker.request_shutdown()

    # disconnect() debe haber sido llamado para garantizar enable_device()
    assert mock_reader.disconnect.called
    assert worker._current_reader is None


def test_worker_run_once(mock_bundle):
    mock_reader = MagicMock()
    mock_reader.get_raw_logs.return_value = []

    worker = AttendanceWorker(
        get_bundle_fn=lambda: mock_bundle,
        interval_seconds=60,
        default_reader=mock_reader,
        once=True,
    )

    ret = worker.start()
    assert ret == 0
    assert mock_reader.connect.called

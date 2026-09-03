"""Pruebas para PersistenceFactory y orquestación con casos de uso reales."""

from datetime import date, datetime, time

import pytest

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryDeviceRepository,
    InMemoryRotationPatternRepository,
    InMemoryShiftRepository,
)
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.adapters.persistence.sql.repositories import (
    SqlAttendanceRepository,
    SqlDeviceRepository,
    SqlRotationPatternRepository,
    SqlShiftRepository,
)
from attendance.application.attendance.process_daily_attendance import ProcessDailyAttendance
from attendance.application.device import sync_all_active_devices
from attendance.domain.device.device import Device
from attendance.domain.device.enums import AuthMethod, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, ShiftCategory, Weekday
from attendance.domain.schedule.shift import ShiftDefinition, ShiftSegment


def test_factory_creates_memory_bundle() -> None:
    bundle = PersistenceFactory.create_bundle("memory")
    assert isinstance(bundle.attendance_repo, InMemoryAttendanceRepository)
    assert isinstance(bundle.device_repo, InMemoryDeviceRepository)
    assert isinstance(bundle.shift_repo, InMemoryShiftRepository)
    assert isinstance(bundle.rotation_pattern_repo, InMemoryRotationPatternRepository)
    assert bundle.database is None


def test_factory_creates_sqlite_bundle() -> None:
    bundle = PersistenceFactory.create_bundle(
        "sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    assert isinstance(bundle.attendance_repo, SqlAttendanceRepository)
    assert isinstance(bundle.device_repo, SqlDeviceRepository)
    assert isinstance(bundle.shift_repo, SqlShiftRepository)
    assert isinstance(bundle.rotation_pattern_repo, SqlRotationPatternRepository)
    assert bundle.database is not None




def test_factory_missing_optional_driver_raises_helpful_error() -> None:
    # Verificamos que si se pide postgres o mongo y falta la librería se notifique con instrucción de instalación
    with pytest.raises(RuntimeError) as exc_info:
        PersistenceFactory.create_bundle(
            "postgres", connection_string="postgresql+psycopg://user:pass@localhost/db"
        )
    assert "pip install 'asistpy[postgres]'" in str(exc_info.value)


def test_end_to_end_use_case_with_sql_bundle() -> None:
    """Valida que un caso de uso central del dominio funcione idénticamente con el bundle SQL."""
    bundle = PersistenceFactory.create_bundle(
        "sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )

    # 1. Registrar empleado en SQL
    emp = Employee(
        id=None,
        pin="EMP007",
        first_name="James",
        paternal_last_name="Bond",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        position="Agente",
        home_branch_id=1,
        active=True,
    )
    bundle.employee_repo.save(emp)

    # 2. Guardar turno en catálogo SQL y asignar al empleado
    shift = ShiftDefinition(
        id=None,
        name="Turno 9 a 18",
        category=ShiftCategory.MATUTINO,
        start_time=time(9, 0),
        end_time=time(18, 0),
        tolerance_minutes=15,
        segments=[ShiftSegment(start_time=time(9, 0), end_time=time(18, 0), tolerance_minutes=15)],
    )
    saved_shift = bundle.shift_repo.save(shift)
    assert saved_shift.id is not None

    assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin="EMP007",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=saved_shift.id,
        working_weekdays={Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY},
    )
    bundle.schedule_assignment_repo.save(assignment)

    # 3. Guardar marcaciones crudas del biométrico
    target_date = date(2026, 3, 2)  # Lunes
    bundle.attendance_repo.save_raw_log(
        AttendanceLog(
            id=None,
            record_uid=1,
            employee_pin="EMP007",
            device_id=1,
            timestamp=datetime(2026, 3, 2, 8, 55),
            auth_method=AuthMethod.FACE,
            processing_status=LogStatus.RAW,
        )
    )
    bundle.attendance_repo.save_raw_log(
        AttendanceLog(
            id=None,
            record_uid=2,
            employee_pin="EMP007",
            device_id=1,
            timestamp=datetime(2026, 3, 2, 18, 5),
            auth_method=AuthMethod.FACE,
            processing_status=LogStatus.RAW,
        )
    )

    # 4. Ejecutar el caso de uso del dominio ProcessDailyAttendance con repositorios SQL
    processor = ProcessDailyAttendance(
        attendance_repo=bundle.attendance_repo,
        daily_attendance_repo=bundle.daily_attendance_repo,
        schedule_assignment_repo=bundle.schedule_assignment_repo,
        shift_repo=bundle.shift_repo,
        rotation_pattern_repo=bundle.rotation_pattern_repo,
        incidence_repo=bundle.incidence_repo,
    )

    result = processor.execute("EMP007", target_date)

    # 5. Aserciones
    assert result.employee_pin == "EMP007"
    assert result.date == target_date
    assert result.tardiness_minutes == 0
    assert result.total_worked_minutes == 550  # 8:55 a 18:05 = 9h 10m = 550m
    assert len(result.sessions) == 1

    # 6. Verificar que quedó guardado en la base de datos relacional
    persisted = bundle.daily_attendance_repo.get_by_employee_and_date("EMP007", target_date)
    assert persisted is not None
    assert persisted.total_worked_minutes == 550
    assert len(persisted.sessions) == 1

    # 7. Verificar que las marcaciones crudas fueron marcadas como procesadas en SQL
    unprocessed = bundle.attendance_repo.get_unprocessed_logs()
    assert len(unprocessed) == 0


class FakeReader:
    def __init__(self, logs: list[AttendanceLog]) -> None:
        self.logs = logs

    def connect(self, device: Device) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def get_raw_logs(self, device: Device) -> list[AttendanceLog]:
        return self.logs

    def get_device_info(self, device: Device) -> dict:
        return {}


def test_end_to_end_device_sync_with_sql_bundle() -> None:
    """Valida que SyncAllActiveDevices funcione sobre un bundle de SQLite."""
    bundle = PersistenceFactory.create_bundle(
        "sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )

    # 1. Registrar dispositivo en SQL
    dev = Device(
        id=None,
        name="Reloj Puerta Principal",
        branch_id=1,
        serial_number="ZK-TEST-001",
        ip_address="192.168.1.200",
        active=True,
    )
    saved_dev = bundle.device_repo.save(dev)
    assert saved_dev.id is not None
    dev_id = saved_dev.id

    # 2. Preparar marcaciones simuladas
    logs = [
        AttendanceLog(
            id=None,
            record_uid=1,
            employee_pin="EMP999",
            device_id=dev_id,
            timestamp=datetime(2026, 3, 1, 8, 0),
            auth_method=AuthMethod.FINGERPRINT,
            processing_status=LogStatus.RAW,
        ),
        AttendanceLog(
            id=None,
            record_uid=2,
            employee_pin="EMP999",
            device_id=dev_id,
            timestamp=datetime(2026, 3, 1, 17, 0),
            auth_method=AuthMethod.FINGERPRINT,
            processing_status=LogStatus.RAW,
        ),
    ]
    reader = FakeReader(logs)

    # 3. Ejecutar orquestador SyncAllActiveDevices
    sync_result = sync_all_active_devices(
        device_registry=bundle.device_repo,
        attendance_repo=bundle.attendance_repo,
        sync_state_repo=bundle.sync_state_repo,
        reader=reader,
    )

    assert sync_result.total_devices == 1
    assert sync_result.successful_devices == 1
    assert sync_result.total_synced_logs == 2

    # 4. Verificar marcaciones crudas guardadas en la base de datos SQL
    unprocessed = bundle.attendance_repo.get_unprocessed_logs()
    assert len(unprocessed) == 2
    assert unprocessed[0].employee_pin == "EMP999"
    assert unprocessed[1].record_uid == 2

    # 5. Verificar marca de agua actualizada en SQL
    last_uid = bundle.sync_state_repo.get_last_synced_uid(dev_id)
    assert last_uid == 2


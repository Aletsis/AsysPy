"""Pruebas de integración para todos los repositorios SQL usando SQLite en memoria."""

from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.database import init_db
from attendance.adapters.persistence.sql.repositories import (
    SqlAttendanceRepository,
    SqlAuditLogRepository,
    SqlDailyAttendanceRepository,
    SqlDeviceRepository,
    SqlEmployeeRepository,
    SqlIncidenceRepository,
    SqlRotationPatternRepository,
    SqlScheduleAssignmentRepository,
    SqlShiftRepository,
    SqlSyncStateRepository,
)
from attendance.domain.attendance.daily_attendance import DailyAttendance
from attendance.domain.attendance.enums import AttendanceStatus, SessionStatus, SessionType
from attendance.domain.attendance.session import WorkSession
from attendance.domain.audit.audit_log import AuditAction, AuditLog
from attendance.domain.device.device import Device, DeviceCapabilities
from attendance.domain.device.enums import AuthMethod, DeviceProtocol, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.incidence.enums import JustificationStatus, JustificationType
from attendance.domain.incidence.justification import Justification
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import (
    AssignmentMode,
    RotationFrequency,
    ShiftCategory,
    Weekday,
)
from attendance.domain.schedule.rotation import RotationPattern
from attendance.domain.schedule.shift import ShiftDefinition, ShiftSegment


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    """Fixture que crea una base de datos SQLite en memoria con esquema inicializado."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    init_db(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# ============================================================================
# Test SqlAttendanceRepository
# ============================================================================
def test_sql_attendance_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlAttendanceRepository(session_factory)

    log1 = AttendanceLog(
        id=None,
        record_uid=101,
        employee_pin="EMP001",
        device_id=1,
        timestamp=datetime(2026, 3, 1, 8, 0, 0),
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )
    repo.save_raw_log(log1)
    assert log1.id is not None

    # Obtener no procesados
    unprocessed = repo.get_unprocessed_logs()
    assert len(unprocessed) == 1
    assert unprocessed[0].employee_pin == "EMP001"

    # Marcar como procesado
    repo.mark_as_processed(log1.id, inferred_type="daily_check_in")
    fetched = repo.get_by_id(log1.id)
    assert fetched is not None
    assert fetched.processing_status == LogStatus.PROCESSED
    assert fetched.inferred_type == "daily_check_in"
    assert len(repo.get_unprocessed_logs()) == 0

    # Consulta por empleado y fecha
    logs_date = repo.get_logs_by_employee_and_date("EMP001", date(2026, 3, 1))
    assert len(logs_date) == 1

    # Actualización de log
    fetched.raw_status = 5
    repo.update_log(fetched)
    updated = repo.get_by_id(log1.id)
    assert updated is not None
    assert updated.raw_status == 5


# ============================================================================
# Test SqlEmployeeRepository
# ============================================================================
def test_sql_employee_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlEmployeeRepository(session_factory)

    emp = Employee(
        id=None,
        pin="EMP100",
        first_name="Carlos",
        paternal_last_name="Gómez",
        maternal_last_name="Ruiz",
        hire_date=date(2025, 1, 15),
        sex=Sex.MALE,
        department_id=2,
        position="Desarrollador",
        home_branch_id=10,
        active=True,
    )
    saved = repo.save(emp)
    assert saved.id is not None

    by_pin = repo.get_by_pin("EMP100")
    assert by_pin is not None
    assert by_pin.full_name == "Carlos Gómez Ruiz"

    by_id = repo.get_by_id(saved.id)
    assert by_id is not None
    assert by_id.pin == "EMP100"

    active_list = repo.list_active(branch_id=10)
    assert len(active_list) == 1

    # Desactivar y verificar
    by_pin.active = False
    by_pin.position_id = 99
    repo.save(by_pin)
    assert len(repo.list_active(branch_id=10)) == 0
    assert len(repo.list_all(branch_id=10)) == 1
    assert repo.count(branch_id=10) == 1
    assert repo.count(branch_id=10, active_only=True) == 0
    assert repo.count(position_id=99) == 1
    assert repo.exists_by_pin("EMP100") is True
    assert repo.exists_by_id(saved.id) is True

    # Eliminar por ID
    assert repo.delete_by_id(saved.id) is True
    assert repo.exists_by_id(saved.id) is False
    assert repo.count() == 0


# ============================================================================
# Test SqlDailyAttendanceRepository
# ============================================================================
def test_sql_daily_attendance_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlDailyAttendanceRepository(session_factory)

    shift = ShiftDefinition(
        id=1,
        name="Turno Matutino",
        category=ShiftCategory.MATUTINO,
        start_time=time(9, 0),
        end_time=time(18, 0),
        tolerance_minutes=10,
        segments=[
            ShiftSegment(start_time=time(9, 0), end_time=time(18, 0), tolerance_minutes=10)
        ],
    )

    session1 = WorkSession(
        id=None,
        employee_pin="EMP001",
        check_in=datetime(2026, 3, 1, 9, 5),
        check_out=datetime(2026, 3, 1, 18, 0),
        session_type=SessionType.REGULAR_WORK,
        status=SessionStatus.CLOSED,
    )

    daily = DailyAttendance(
        employee_pin="EMP001",
        date=date(2026, 3, 1),
        expected_shift=shift,
        sessions=[session1],
        status=AttendanceStatus.PRESENT,
        tardiness_minutes=5,
    )

    saved = repo.save(daily)
    assert len(saved.sessions) == 1
    assert saved.total_worked_minutes > 0

    fetched = repo.get_by_employee_and_date("EMP001", date(2026, 3, 1))
    assert fetched is not None
    assert fetched.employee_pin == "EMP001"
    assert fetched.status == AttendanceStatus.PRESENT
    assert fetched.expected_shift is not None
    assert fetched.expected_shift.name == "Turno Matutino"
    assert len(fetched.sessions) == 1

    # Modificar y guardar de nuevo (upsert)
    fetched.notes = "Revisión aprobada por RH"
    repo.save(fetched)
    updated = repo.get_by_employee_and_date("EMP001", date(2026, 3, 1))
    assert updated is not None
    assert updated.notes == "Revisión aprobada por RH"

    # Rango de fechas
    range_records = repo.get_by_employee_and_date_range(
        "EMP001", date(2026, 3, 1), date(2026, 3, 2)
    )
    assert len(range_records) == 1


# ============================================================================
# Test SqlIncidenceRepository
# ============================================================================
def test_sql_incidence_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlIncidenceRepository(session_factory)

    justification = Justification(
        id=None,
        employee_pin="EMP001",
        type=JustificationType.IMSS_INCAPACITY,
        start_date=date(2026, 3, 5),
        end_date=date(2026, 3, 7),
        reason="Incapacidad médica IMSS",
        approved_by="Dr. Gómez",
        status=JustificationStatus.APPROVED,
        support_document="FOLIO-998877",
    )
    saved = repo.save(justification)
    assert saved.id is not None

    active = repo.get_active_justification("EMP001", date(2026, 3, 6))
    assert active is not None
    assert active.support_document == "FOLIO-998877"

    not_active = repo.get_active_justification("EMP001", date(2026, 3, 8))
    assert not_active is None

    emp_list = repo.list_by_employee("EMP001")
    assert len(emp_list) == 1


# ============================================================================
# Test SqlScheduleAssignmentRepository
# ============================================================================
def test_sql_schedule_assignment_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlScheduleAssignmentRepository(session_factory)

    assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin="EMP001",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        valid_until=None,
        working_weekdays={Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY},
        shift_definition_id=1,
    )
    saved = repo.save(assignment)
    assert saved.id is not None

    active = repo.get_active_assignment("EMP001", date(2026, 3, 1))
    assert active is not None
    assert active.shift_definition_id == 1
    assert active.working_weekdays is not None
    assert Weekday.MONDAY in active.working_weekdays

    # Cerrar asignación
    repo.close_assignment(saved.id, valid_until=date(2026, 3, 31))
    closed = repo.get_active_assignment("EMP001", date(2026, 4, 1))
    assert closed is None


# ============================================================================
# Test SqlAuditLogRepository
# ============================================================================
def test_sql_audit_log_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlAuditLogRepository(session_factory)

    audit = AuditLog(
        id=None,
        entity_type="attendance_log",
        entity_id=123,
        action=AuditAction.PUNCH_UPDATED,
        performed_by="admin@empresa.com",
        reason="Corrección de hora por falla de luz",
        previous_value={"timestamp": "2026-03-01T08:00:00"},
        new_value={"timestamp": "2026-03-01T08:30:00"},
        employee_pin="EMP001",
    )
    saved = repo.save(audit)
    assert saved.id is not None

    by_entity = repo.list_by_entity("attendance_log", 123)
    assert len(by_entity) == 1
    assert by_entity[0].performed_by == "admin@empresa.com"

    by_emp = repo.list_by_employee("EMP001")
    assert len(by_emp) == 1


# ============================================================================
# Test SqlSyncStateRepository
# ============================================================================
def test_sql_sync_state_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlSyncStateRepository(session_factory)

    # Inicialmente debe retornar 0
    assert repo.get_last_synced_uid(1) == 0

    repo.update_last_synced_uid(1, 450)
    assert repo.get_last_synced_uid(1) == 450

    repo.update_last_synced_uid(1, 480)
    assert repo.get_last_synced_uid(1) == 480


# ============================================================================
# Test SqlDeviceRepository
# ============================================================================
def test_sql_device_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlDeviceRepository(session_factory)

    now = datetime(2026, 3, 1, 12, 0, 0)
    caps = DeviceCapabilities(
        firmware_version="v8.0.1",
        platform="Linux/ARM",
        manufacturer_device_name="ZKTeco MB360",
        mac_address="00:11:22:33:44:55",
        last_read_at=now,
    )

    dev1 = Device(
        id=None,
        name="Reloj Entrada Principal",
        branch_id=10,
        protocol=DeviceProtocol.TCP_4370,
        serial_number="ZK-SN-001",
        ip_address="192.168.1.201",
        port=4370,
        location_label="Recepción Edificio A",
        capabilities=caps,
        active=True,
    )

    # 1. Guardar y verificar autoincremento de ID
    saved1 = repo.save(dev1)
    assert saved1.id is not None
    assert saved1.id > 0
    dev1_id = saved1.id

    # 2. Consultar por ID y validar capabilities JSON
    fetched = repo.get_by_id(dev1_id)
    assert fetched is not None
    assert fetched.name == "Reloj Entrada Principal"
    assert fetched.serial_number == "ZK-SN-001"
    assert fetched.capabilities is not None
    assert fetched.capabilities.firmware_version == "v8.0.1"
    assert fetched.capabilities.last_read_at == now
    assert fetched.capabilities.mac_address == "00:11:22:33:44:55"

    # 3. Consultar por serial_number
    by_serial = repo.get_by_serial_number("ZK-SN-001")
    assert by_serial is not None
    assert by_serial.id == dev1_id

    assert repo.get_by_serial_number("NO_EXISTE") is None

    # 4. Guardar segundo dispositivo (inactivo) en otra sucursal
    dev2 = Device(
        id=None,
        name="Reloj Almacén",
        branch_id=20,
        serial_number="ZK-SN-002",
        active=False,
    )
    saved2 = repo.save(dev2)
    assert saved2.id is not None

    # 5. Listar activos
    active_all = repo.get_active_devices()
    assert len(active_all) == 1
    assert active_all[0].id == dev1_id

    # Filtrar activos por sucursal
    assert len(repo.get_active_devices(branch_id=10)) == 1
    assert len(repo.get_active_devices(branch_id=20)) == 0

    # 6. Listar todos
    assert len(repo.list_all()) == 2
    assert len(repo.list_all(branch_id=20)) == 1

    # 7. Actualización (Upsert)
    fetched.name = "Reloj Entrada Modificado"
    fetched.active = False
    repo.save(fetched)

    updated = repo.get_by_id(dev1_id)
    assert updated is not None
    assert updated.name == "Reloj Entrada Modificado"
    assert updated.active is False
    assert len(repo.get_active_devices()) == 0


# ============================================================================
# Test SqlShiftRepository
# ============================================================================
def test_sql_shift_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlShiftRepository(session_factory)

    # 1. Guardar turno continuo (Matutino 08:00 - 16:00)
    morning_shift = ShiftDefinition(
        id=None,
        name="Turno Matutino",
        category=ShiftCategory.MATUTINO,
        start_time=time(8, 0),
        end_time=time(16, 0),
        tolerance_minutes=15,
    )
    saved_morning = repo.save(morning_shift)
    assert saved_morning.id is not None
    morning_id = saved_morning.id

    # 2. Consultar por ID
    fetched_morning = repo.get_by_id(morning_id)
    assert fetched_morning is not None
    assert fetched_morning.name == "Turno Matutino"
    assert fetched_morning.category == ShiftCategory.MATUTINO
    assert fetched_morning.start_time == time(8, 0)
    assert fetched_morning.end_time == time(16, 0)
    assert fetched_morning.tolerance_minutes == 15
    assert not fetched_morning.crosses_midnight
    assert not fetched_morning.is_split
    assert len(fetched_morning.segments) == 1

    # 3. Guardar turno partido (Comercio 09:00-14:00 y 16:00-19:00)
    split_shift = ShiftDefinition(
        id=None,
        name="Comercio Partido",
        category=ShiftCategory.MIXTO,
        segments=[
            ShiftSegment(start_time=time(9, 0), end_time=time(14, 0), tolerance_minutes=10, name="Mañana"),
            ShiftSegment(start_time=time(16, 0), end_time=time(19, 0), tolerance_minutes=5, name="Tarde"),
        ],
    )
    saved_split = repo.save(split_shift)
    assert saved_split.id is not None
    split_id = saved_split.id

    fetched_split = repo.get_by_id(split_id)
    assert fetched_split is not None
    assert fetched_split.is_split
    assert len(fetched_split.segments) == 2
    assert fetched_split.expected_work_minutes == 480

    # 4. Guardar turno nocturno / 24 Horas que cruza medianoche (24x48)
    night_24_shift = ShiftDefinition(
        id=None,
        name="Turno 24 Horas",
        category=ShiftCategory.NOCTURNO,
        start_time=time(8, 0),
        end_time=time(7, 59),
        crosses_midnight=True,
        tolerance_minutes=15,
    )
    saved_24 = repo.save(night_24_shift)
    assert saved_24.id is not None
    assert saved_24.crosses_midnight

    # 5. Listar todos
    all_shifts = repo.list_all()
    assert len(all_shifts) == 3

    # 6. Actualizar turno
    fetched_morning.name = "Matutino Modificado"
    fetched_morning.tolerance_minutes = 20
    repo.save(fetched_morning)

    updated_morning = repo.get_by_id(morning_id)
    assert updated_morning is not None
    assert updated_morning.name == "Matutino Modificado"
    assert updated_morning.tolerance_minutes == 20

    # 7. Eliminar turno
    assert repo.delete(split_id) is True
    assert repo.get_by_id(split_id) is None
    assert len(repo.list_all()) == 2
    assert repo.delete(9999) is False


# ============================================================================
# Test SqlRotationPatternRepository
# ============================================================================
def test_sql_rotation_pattern_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlRotationPatternRepository(session_factory)

    # 1. Guardar patrón 6x1
    pattern_6x1 = RotationPattern(
        id=None,
        name="Patrón 6x1",
        shift_sequence=[1, 1, 1, 1, 1, 1, None],
        frequency=RotationFrequency.DAILY,
        anchor_date=date(2026, 1, 1),
    )
    saved_6x1 = repo.save(pattern_6x1)
    assert saved_6x1.id is not None
    p_id = saved_6x1.id

    # 2. Consultar por ID
    fetched_6x1 = repo.get_by_id(p_id)
    assert fetched_6x1 is not None
    assert fetched_6x1.name == "Patrón 6x1"
    assert fetched_6x1.frequency == RotationFrequency.DAILY
    assert fetched_6x1.anchor_date == date(2026, 1, 1)
    assert fetched_6x1.shift_sequence == [1, 1, 1, 1, 1, 1, None]
    assert fetched_6x1.resolve_shift_id(date(2026, 1, 1)) == 1
    assert fetched_6x1.resolve_shift_id(date(2026, 1, 7)) is None

    # 3. Guardar patrón 24x48 (1 día de turno 24h y 2 días de descanso)
    pattern_24x48 = RotationPattern(
        id=None,
        name="Patrón 24x48",
        shift_sequence=[2, None, None],
        frequency=RotationFrequency.DAILY,
        anchor_date=date(2026, 1, 1),
    )
    saved_24x48 = repo.save(pattern_24x48)
    assert saved_24x48.id is not None
    p24_id = saved_24x48.id

    # 4. Listar todos
    all_patterns = repo.list_all()
    assert len(all_patterns) == 2

    # 5. Actualizar patrón
    fetched_6x1.name = "6x1 Modificado"
    repo.save(fetched_6x1)

    updated_6x1 = repo.get_by_id(p_id)
    assert updated_6x1 is not None
    assert updated_6x1.name == "6x1 Modificado"

    # 6. Eliminar patrón
    assert repo.delete(p24_id) is True
    assert repo.get_by_id(p24_id) is None
    assert len(repo.list_all()) == 1
    assert repo.delete(9999) is False



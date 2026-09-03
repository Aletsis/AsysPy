"""Pruebas para PersistenceFactory y orquestación con casos de uso reales."""

from datetime import date, datetime, time

import pytest

from attendance.adapters.memory import InMemoryAttendanceRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.adapters.persistence.sql.repositories import SqlAttendanceRepository
from attendance.application.attendance.process_daily_attendance import ProcessDailyAttendance
from attendance.domain.device.enums import AuthMethod, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, ShiftCategory, Weekday
from attendance.domain.schedule.shift import ShiftDefinition, ShiftSegment


def test_factory_creates_memory_bundle() -> None:
    bundle = PersistenceFactory.create_bundle("memory")
    assert isinstance(bundle.attendance_repo, InMemoryAttendanceRepository)
    assert bundle.database is None


def test_factory_creates_sqlite_bundle() -> None:
    bundle = PersistenceFactory.create_bundle(
        "sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    assert isinstance(bundle.attendance_repo, SqlAttendanceRepository)
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

    # 2. Asignar turno
    shift = ShiftDefinition(
        id=1,
        name="Turno 9 a 18",
        category=ShiftCategory.MATUTINO,
        start_time=time(9, 0),
        end_time=time(18, 0),
        tolerance_minutes=15,
        segments=[ShiftSegment(start_time=time(9, 0), end_time=time(18, 0), tolerance_minutes=15)],
    )
    assignment = EmployeeScheduleAssignment(
        id=None,
        employee_pin="EMP007",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
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
        shift_definitions={1: shift},
        rotation_patterns={},
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

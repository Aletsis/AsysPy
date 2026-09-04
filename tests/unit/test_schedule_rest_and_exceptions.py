"""Pruebas unitarias e integración para descanso fijo, rotativo y eventualidades de horario."""

from datetime import date, datetime, time
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.cli.main import main
from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryDailyAttendanceRepository,
    InMemoryRotationPatternRepository,
    InMemoryScheduleAssignmentRepository,
    InMemoryScheduleExceptionRepository,
    InMemoryShiftRepository,
)
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.adapters.persistence.sql.database import init_db
from attendance.adapters.persistence.sql.repositories import SqlScheduleExceptionRepository
from attendance.application.attendance.process_daily_attendance import ProcessDailyAttendance
from attendance.domain.attendance.enums import AttendanceStatus
from attendance.domain.device.enums import AuthMethod, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, Weekday
from attendance.domain.schedule.exception import ScheduleException
from attendance.domain.schedule.shift import ShiftDefinition


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:", echo=False)
    init_db(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_sql_schedule_exception_repository(session_factory: sessionmaker[Session]) -> None:
    repo = SqlScheduleExceptionRepository(session_factory)

    # 1. Guardar excepción de descanso forzado (shift_definition_id = None)
    exc1 = ScheduleException(
        id=None,
        employee_pin="E100",
        date=date(2026, 3, 15),
        shift_definition_id=None,
        reason="Cambio de descanso acordado con jefatura",
    )
    saved1 = repo.save(exc1)
    assert saved1.id is not None
    assert saved1.employee_pin == "E100"
    assert saved1.date == date(2026, 3, 15)
    assert saved1.shift_definition_id is None
    assert saved1.reason == "Cambio de descanso acordado con jefatura"

    # 2. Guardar excepción de turno forzado
    exc2 = ScheduleException(
        id=None,
        employee_pin="E100",
        date=date(2026, 3, 16),
        shift_definition_id=2,
        reason="Cobertura de turno nocturno",
    )
    saved2 = repo.save(exc2)
    assert saved2.id is not None
    assert saved2.shift_definition_id == 2

    # 3. get_by_id
    fetched = repo.get_by_id(saved1.id)
    assert fetched is not None
    assert fetched.reason == "Cambio de descanso acordado con jefatura"

    # 4. get_by_employee_and_date
    by_date = repo.get_by_employee_and_date("E100", date(2026, 3, 15))
    assert by_date is not None
    assert by_date.id == saved1.id

    # 5. list_for_employee con rango
    emp_list = repo.list_for_employee("E100", start_date=date(2026, 3, 1), end_date=date(2026, 3, 31))
    assert len(emp_list) == 2

    # 6. list_for_date
    date_list = repo.list_for_date(date(2026, 3, 15))
    assert len(date_list) == 1
    assert date_list[0].employee_pin == "E100"

    # 7. Upsert sobre la misma fecha
    exc_update = ScheduleException(
        id=None,
        employee_pin="E100",
        date=date(2026, 3, 15),
        shift_definition_id=1,
        reason="Actualización a turno 1",
    )
    updated = repo.save(exc_update)
    assert updated.shift_definition_id == 1
    assert updated.reason == "Actualización a turno 1"

    # 8. delete
    assert repo.delete(saved2.id) is True
    assert repo.get_by_id(saved2.id) is None
    assert repo.delete(9999) is False


def test_in_memory_schedule_exception_repository() -> None:
    repo = InMemoryScheduleExceptionRepository()
    exc = ScheduleException(
        id=None,
        employee_pin="E200",
        date=date(2026, 5, 10),
        shift_definition_id=None,
        reason="Descanso compensatorio",
    )
    saved = repo.save(exc)
    assert saved.id == 1
    assert repo.get_by_id(1) is not None
    assert repo.get_by_employee_and_date("E200", date(2026, 5, 10)) is not None
    assert len(repo.list_all()) == 1
    assert repo.delete(1) is True
    assert repo.get_by_id(1) is None


def test_process_daily_attendance_with_rest_days_and_eventualities() -> None:
    """Verifica que ProcessDailyAttendance resuelva descanso semanal y eventualidades."""
    shift = ShiftDefinition(
        id=1,
        name="Matutino 08:00 - 16:00",
        start_time=time(8, 0),
        end_time=time(16, 0),
        tolerance_minutes=15,
    )
    # Asignación Lunes a Viernes (Descanso Sábado y Domingo)
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="E100",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
        working_weekdays={
            Weekday.MONDAY,
            Weekday.TUESDAY,
            Weekday.WEDNESDAY,
            Weekday.THURSDAY,
            Weekday.FRIDAY,
        },
    )

    attendance_repo = InMemoryAttendanceRepository()
    daily_repo = InMemoryDailyAttendanceRepository()
    assign_repo = InMemoryScheduleAssignmentRepository([assignment])
    shift_repo = InMemoryShiftRepository([shift])
    rot_repo = InMemoryRotationPatternRepository()
    exc_repo = InMemoryScheduleExceptionRepository()

    processor = ProcessDailyAttendance(
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assign_repo,
        shift_repo=shift_repo,
        rotation_pattern_repo=rot_repo,
        schedule_exception_repo=exc_repo,
    )

    # 1. Día habitual laborable (Miércoles 2026-03-11) sin checadas -> ABSENT
    wednesday = date(2026, 3, 11)
    res_wed = processor.execute("E100", wednesday)
    assert res_wed.status == AttendanceStatus.ABSENT

    # 2. Día de descanso semanal habitual (Domingo 2026-03-15) sin checadas -> REST_DAY
    sunday = date(2026, 3, 15)
    res_sun = processor.execute("E100", sunday)
    assert res_sun.status == AttendanceStatus.REST_DAY

    # 3. Día de descanso semanal habitual con checadas -> PRESENT con nota
    punch_in = AttendanceLog(
        id=None,
        record_uid=1,
        employee_pin="E100",
        device_id=1,
        timestamp=datetime(2026, 3, 15, 8, 0),
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )
    punch_out = AttendanceLog(
        id=None,
        record_uid=2,
        employee_pin="E100",
        device_id=1,
        timestamp=datetime(2026, 3, 15, 16, 0),
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )
    attendance_repo.save_raw_log(punch_in)
    attendance_repo.save_raw_log(punch_out)
    res_sun_worked = processor.execute("E100", sunday)
    assert res_sun_worked.status == AttendanceStatus.PRESENT
    assert res_sun_worked.notes == "Laboró en día de descanso"

    # 4. EVENTUALIDAD: Forzar descanso en día laborable (Miércoles 2026-03-18)
    next_wed = date(2026, 3, 18)
    exc_repo.save(
        ScheduleException(
            id=None,
            employee_pin="E100",
            date=next_wed,
            shift_definition_id=None,  # Descanso forzado
            reason="Intercambio de día de descanso por evento",
        )
    )
    res_eventuality_rest = processor.execute("E100", next_wed)
    assert res_eventuality_rest.status == AttendanceStatus.REST_DAY

    # 5. EVENTUALIDAD: Forzar turno en día de descanso habitual (Sábado 2026-03-21)
    saturday = date(2026, 3, 21)
    exc_repo.save(
        ScheduleException(
            id=None,
            employee_pin="E100",
            date=saturday,
            shift_definition_id=1,  # Forzar turno matutino
            reason="Turno extraordinario sabatino",
        )
    )
    # Sin checadas en ese sábado forzado -> Debe marcarse ABSENT (le tocaba trabajar ese turno)
    res_eventuality_shift = processor.execute("E100", saturday)
    assert res_eventuality_shift.status == AttendanceStatus.ABSENT


def test_cli_schedule_rest_days_and_exceptions(capsys) -> None:
    """Verifica que los comandos CLI de schedule soporten --rest-days, rotation y exceptions."""
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # Crear empleado y turno
        main(["employee", "add", "--pin", "E500", "--first-name", "Laura", "--paternal-last-name", "Torres"])
        main(["shift", "add", "--name", "Regular 08-16", "--start-time", "08:00", "--end-time", "16:00"])
        capsys.readouterr()

        # 1. Asignar con --rest-days domingo
        code = main([
            "schedule",
            "assign",
            "--employee-pin",
            "E500",
            "--shift-id",
            "1",
            "--mode",
            "fixed",
            "--rest-days",
            "domingo",
            "--valid-from",
            "2026-09-01",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Horario asignado exitosamente" in out
        assert "Descanso: Dom" in out

        # 2. Consultar show
        code = main(["schedule", "show", "--assignment-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Descanso: Dom" in out

        # 3. Crear patrón rotativo 6x1
        code = main([
            "schedule",
            "rotation",
            "add",
            "--name",
            "Rotativo 6x1",
            "--sequence",
            "1,1,1,1,1,1,OFF",
            "--frequency",
            "daily",
            "--anchor-date",
            "2026-09-01",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Rotativo 6x1" in out
        assert "registrado con ID 1" in out

        # 4. Listar patrones rotativos
        code = main(["schedule", "rotation", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Rotativo 6x1" in out
        assert "6 Trab. / 1 Desc." in out

        # 5. Registrar eventualidad de descanso forzado
        code = main([
            "schedule",
            "exception",
            "add",
            "--employee-pin",
            "E500",
            "--date",
            "2026-09-15",
            "--rest-day",
            "--reason",
            "Descanso compensatorio especial",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Eventualidad de horario registrada exitosamente" in out
        assert "DESCANSO FORZADO" in out

        # 6. Listar eventualidades
        code = main(["schedule", "exception", "list", "--employee-pin", "E500"])
        assert code == 0
        out = capsys.readouterr().out
        assert "2026-09-15" in out
        assert "Descanso compensatorio especial" in out

        # 7. Eliminar eventualidad
        code = main(["schedule", "exception", "delete", "--exception-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminada correctamente" in out

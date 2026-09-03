"""Pruebas unitarias para ajuste manual de marcaciones con trazabilidad de auditoría."""

from datetime import date, datetime, time

import pytest

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryAuditLogRepository,
    InMemoryDailyAttendanceRepository,
    InMemoryScheduleAssignmentRepository,
)
from attendance.application.adjustment import (
    cancel_punch,
    create_manual_punch,
    modify_punch_timestamp,
)
from attendance.application.attendance import process_daily_attendance
from attendance.domain.attendance import AttendanceStatus
from attendance.domain.audit import AuditAction
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.device import AttendanceLog, AuthMethod, LogStatus
from attendance.domain.schedule import (
    AssignmentMode,
    EmployeeScheduleAssignment,
    ShiftCategory,
    ShiftDefinition,
)

SHIFT_8_17 = ShiftDefinition(
    id=1,
    name="Turno 8 a 17",
    category=ShiftCategory.MATUTINO,
    start_time=time(8, 0),
    end_time=time(17, 0),
    tolerance_minutes=10,
)
SHIFT_DEFS = {1: SHIFT_8_17}


def test_create_manual_punch_with_audit_trail():
    attendance_repo = InMemoryAttendanceRepository()
    audit_repo = InMemoryAuditLogRepository()

    punch_time = datetime(2026, 3, 10, 8, 0)
    punch = create_manual_punch(
        employee_pin="1001",
        timestamp=punch_time,
        performed_by="rh_admin@empresa.com",
        reason="Checador biométrico no leyó huella",
        attendance_repo=attendance_repo,
        audit_repo=audit_repo,
    )

    assert punch.id is not None
    assert punch.employee_pin == "1001"
    assert punch.auth_method == AuthMethod.MANUAL
    assert punch.processing_status == LogStatus.RAW

    # Verificar registro en repositorio de marcaciones
    saved_punch = attendance_repo.get_by_id(punch.id)
    assert saved_punch is not None
    assert saved_punch.timestamp == punch_time

    # Verificar registro de trazabilidad en auditoría
    audit_logs = audit_repo.list_by_employee("1001")
    assert len(audit_logs) == 1
    audit = audit_logs[0]
    assert audit.action == AuditAction.PUNCH_CREATED
    assert audit.performed_by == "rh_admin@empresa.com"
    assert audit.reason == "Checador biométrico no leyó huella"
    assert audit.new_value is not None
    assert audit.new_value["employee_pin"] == "1001"
    assert audit.new_value["auth_method"] == "manual"


def test_modify_punch_timestamp_with_audit_trail():
    punch_orig = AttendanceLog(
        id=1,
        record_uid=101,
        employee_pin="1001",
        device_id=1,
        timestamp=datetime(2026, 3, 10, 9, 30),  # Marcación con retardo errónea
        raw_status=0,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.PROCESSED,
    )
    attendance_repo = InMemoryAttendanceRepository([punch_orig])
    audit_repo = InMemoryAuditLogRepository()

    new_time = datetime(2026, 3, 10, 8, 0)
    updated = modify_punch_timestamp(
        log_id=1,
        new_timestamp=new_time,
        performed_by="supervisor_planta",
        reason="Corrección por desfase de reloj del checador",
        attendance_repo=attendance_repo,
        audit_repo=audit_repo,
    )

    assert updated.timestamp == new_time
    assert updated.processing_status == LogStatus.RAW  # Se restablece para reprocesar

    # Verificar auditoría
    audit_logs = audit_repo.list_by_entity("attendance_log", 1)
    assert len(audit_logs) == 1
    audit = audit_logs[0]
    assert audit.action == AuditAction.PUNCH_UPDATED
    assert audit.performed_by == "supervisor_planta"
    assert audit.reason == "Corrección por desfase de reloj del checador"
    assert audit.previous_value is not None
    assert audit.previous_value["timestamp"] == datetime(2026, 3, 10, 9, 30).isoformat()
    assert audit.new_value is not None
    assert audit.new_value["timestamp"] == new_time.isoformat()


def test_cancel_punch_marks_ignored_with_audit_trail():
    punch = AttendanceLog(
        id=2,
        record_uid=102,
        employee_pin="1001",
        device_id=1,
        timestamp=datetime(2026, 3, 10, 12, 0),
        raw_status=0,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )
    attendance_repo = InMemoryAttendanceRepository([punch])
    audit_repo = InMemoryAuditLogRepository()

    cancelled = cancel_punch(
        log_id=2,
        performed_by="admin_rh",
        reason="Marcación accidental realizada por otro empleado con PIN similar",
        attendance_repo=attendance_repo,
        audit_repo=audit_repo,
    )

    assert cancelled.processing_status == LogStatus.IGNORED

    # Marcaciones ignoradas no deben salir en las consultas activas para asistencia
    active_logs = attendance_repo.get_logs_by_employee_and_date("1001", date(2026, 3, 10))
    assert len(active_logs) == 0

    # Auditoría presente
    audits = audit_repo.list_by_employee("1001")
    assert len(audits) == 1
    assert audits[0].action == AuditAction.PUNCH_DELETED
    assert audits[0].reason == "Marcación accidental realizada por otro empleado con PIN similar"


def test_audit_validation_requires_performed_by_and_reason():
    attendance_repo = InMemoryAttendanceRepository()
    audit_repo = InMemoryAuditLogRepository()

    with pytest.raises(ValidationError, match="usuario responsable.*obligatorio"):
        create_manual_punch(
            employee_pin="1001",
            timestamp=datetime(2026, 3, 10, 8, 0),
            performed_by="",  # Vacío
            reason="Motivo válido",
            attendance_repo=attendance_repo,
            audit_repo=audit_repo,
        )

    with pytest.raises(ValidationError, match="motivo.*obligatorio"):
        create_manual_punch(
            employee_pin="1001",
            timestamp=datetime(2026, 3, 10, 8, 0),
            performed_by="admin",
            reason="   ",  # Espacios vacíos
            attendance_repo=attendance_repo,
            audit_repo=audit_repo,
        )


def test_end_to_end_manual_adjustment_and_daily_reprocessing():
    """Flujo integral:

    1. Empleado olvida checar salida -> día evaluado como INCOMPLETE.
    2. Administrador registra marcación manual de salida con motivo y trazabilidad de auditoría.
    3. Se reprocesa la jornada del empleado -> pasa a PRESENT.
    """
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    # Horario esperado: 8:00 a 17:00
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Paso 1: Solo checó entrada a las 08:00
    in_punch = AttendanceLog(
        id=1,
        record_uid=1,
        employee_pin=employee_pin,
        device_id=1,
        timestamp=datetime(2026, 3, 10, 8, 0),
        raw_status=0,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )
    attendance_repo = InMemoryAttendanceRepository([in_punch])
    audit_repo = InMemoryAuditLogRepository()
    daily_repo = InMemoryDailyAttendanceRepository()

    initial_daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )
    assert initial_daily.status == AttendanceStatus.INCOMPLETE

    # Paso 2: Supervisor agrega la salida a las 17:00 con auditoría
    out_punch = create_manual_punch(
        employee_pin=employee_pin,
        timestamp=datetime(2026, 3, 10, 17, 0),
        performed_by="supervisor_almacen",
        reason="Olvido de checada justificado por descarga de embarque urgente",
        attendance_repo=attendance_repo,
        audit_repo=audit_repo,
    )
    assert out_punch.auth_method == AuthMethod.MANUAL

    # Verificar que la auditoría está registrada
    audit_records = audit_repo.list_by_employee(employee_pin)
    assert len(audit_records) == 1
    assert audit_records[0].performed_by == "supervisor_almacen"

    # Paso 3: Reprocesar la jornada
    reprocessed_daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    # Ahora la jornada es PRESENT, completada y persistida
    assert reprocessed_daily.status == AttendanceStatus.PRESENT
    assert reprocessed_daily.total_worked_minutes == 540
    assert reprocessed_daily.has_open_sessions is False

    # El repositorio persiste la jornada actualizada
    persisted = daily_repo.get_by_employee_and_date(employee_pin, target_date)
    assert persisted is not None
    assert persisted.status == AttendanceStatus.PRESENT
    assert persisted.total_worked_minutes == 540

"""Pruebas unitarias para el caso de uso central ProcessDailyAttendance."""

from datetime import date, datetime, time

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryDailyAttendanceRepository,
    InMemoryEmployeeRepository,
    InMemoryIncidenceRepository,
    InMemoryScheduleAssignmentRepository,
    InMemorySyncStateRepository,
)
from attendance.application.attendance import (
    ProcessDailyAttendance,
    ProcessDailyAttendanceBatch,
    ProcessEmployeeAttendanceRange,
    process_daily_attendance,
    process_daily_attendance_batch,
    process_employee_attendance_range,
)
from attendance.domain.attendance import AttendanceStatus
from attendance.domain.device import AttendanceLog, AuthMethod, LogStatus
from attendance.domain.incidence import (
    Justification,
    JustificationStatus,
    JustificationType,
)
from attendance.domain.organization import Employee, Sex
from attendance.domain.policy import OvertimePolicy, RoundingMethod
from attendance.domain.schedule import (
    AssignmentMode,
    EmployeeScheduleAssignment,
    ShiftCategory,
    ShiftDefinition,
    ShiftSegment,
    Weekday,
)

# Constantes de turnos
SHIFT_8_17 = ShiftDefinition(
    id=1,
    name="Turno 8 a 17",
    category=ShiftCategory.MATUTINO,
    start_time=time(8, 0),
    end_time=time(17, 0),
    tolerance_minutes=10,
)

NIGHT_SHIFT = ShiftDefinition(
    id=2,
    name="Turno Nocturno 22 a 06",
    category=ShiftCategory.NOCTURNO,
    start_time=time(22, 0),
    end_time=time(6, 0),
    tolerance_minutes=10,
    crosses_midnight=True,
)

SPLIT_SHIFT = ShiftDefinition(
    id=3,
    name="Turno Partido 09-14 y 16-20",
    category=ShiftCategory.PERSONALIZADO,
    segments=[
        ShiftSegment(
            start_time=time(9, 0), end_time=time(14, 0), tolerance_minutes=10, name="Matutino"
        ),
        ShiftSegment(
            start_time=time(16, 0), end_time=time(20, 0), tolerance_minutes=0, name="Vespertino"
        ),
    ],
)

SHIFT_DEFS = {1: SHIFT_8_17, 2: NIGHT_SHIFT, 3: SPLIT_SHIFT}


def make_log(
    pin: str,
    dt: datetime,
    device_id: int = 1,
    log_id: int | None = None,
) -> AttendanceLog:
    return AttendanceLog(
        id=log_id,
        record_uid=int(dt.timestamp()),
        employee_pin=pin,
        device_id=device_id,
        timestamp=dt,
        raw_status=0,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )


def test_process_daily_attendance_punctual_workday():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    # 1. Asignación activa fija
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # 2. Marcaciones de entrada (07:58) y salida (17:02)
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 7, 58)),
        make_log(employee_pin, datetime(2026, 3, 10, 17, 2)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    # Ejecutar caso de uso
    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    # Aserciones
    assert daily.status == AttendanceStatus.PRESENT
    assert daily.tardiness_minutes == 0
    assert daily.early_departure_minutes == 0
    assert daily.total_worked_minutes == 544
    assert daily.first_check_in == datetime(2026, 3, 10, 7, 58)
    assert daily.last_check_out == datetime(2026, 3, 10, 17, 2)

    # Verificar que se guardó en el repositorio
    persisted = daily_repo.get_by_employee_and_date(employee_pin, target_date)
    assert persisted is not None
    assert persisted.status == AttendanceStatus.PRESENT


def test_process_daily_attendance_tardiness_and_early_departure():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Entró a las 08:20 (tolerancia era 10 min -> 20 min retardo)
    # Salió a las 16:30 (salida anticipada de 30 min)
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 8, 20)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 30)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.LATE
    assert daily.tardiness_minutes == 20
    assert daily.early_departure_minutes == 30


def test_process_daily_attendance_with_overtime():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,  # 8 a 17 -> 9h = 540 min
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Salió a las 18:35 -> 1h y 35 min extra (95 min)
    # Con política ROUND_DOWN a 15 min: 90 minutos de tiempo extra
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 18, 35)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    overtime_policy = OvertimePolicy(
        id=1,
        name="Horas Extra 15m",
        overtime_allowed=True,
        rounding_method=RoundingMethod.ROUND_DOWN,
        rounding_interval_minutes=15,
    )

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        overtime_policy=overtime_policy,
    )

    assert daily.status == AttendanceStatus.PRESENT
    assert daily.overtime_minutes == 90


def test_process_daily_attendance_incomplete_open_session():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Solo checó entrada
    logs = [make_log(employee_pin, datetime(2026, 3, 10, 8, 0))]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.INCOMPLETE
    assert daily.has_open_sessions is True


def test_process_daily_attendance_unjustified_absence():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Sin marcaciones
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.ABSENT


def test_process_daily_attendance_justified_absence_vacation():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Justificación de vacaciones aprobada del 9 al 13 de marzo
    justification = Justification(
        id=1,
        employee_pin=employee_pin,
        type=JustificationType.VACATION,
        start_date=date(2026, 3, 9),
        end_date=date(2026, 3, 13),
        reason="Vacaciones primer periodo 2026",
        approved_by="Gerente RH",
        status=JustificationStatus.APPROVED,
    )
    incidence_repo = InMemoryIncidenceRepository([justification])
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        incidence_repo=incidence_repo,
    )

    assert daily.status == AttendanceStatus.JUSTIFIED_ABSENCE
    assert "[VACATION]" in (daily.notes or "")
    assert "Vacaciones primer periodo 2026" in (daily.notes or "")


def test_process_daily_attendance_justified_absence_imss_incapacity():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    justification = Justification(
        id=2,
        employee_pin=employee_pin,
        type=JustificationType.IMSS_INCAPACITY,
        start_date=date(2026, 3, 10),
        end_date=date(2026, 3, 12),
        reason="Incapacidad médica por enfermedad general",
        approved_by="Médico laboral",
        support_document="IMSS-FOLIO-987654",
        status=JustificationStatus.APPROVED,
    )
    incidence_repo = InMemoryIncidenceRepository([justification])
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        incidence_repo=incidence_repo,
    )

    assert daily.status == AttendanceStatus.JUSTIFIED_ABSENCE
    assert "[IMSS_INCAPACITY]" in (daily.notes or "")
    assert "IMSS-FOLIO-987654" in (daily.notes or "")


def test_process_daily_attendance_night_shift_crossing_midnight():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=2,  # Turno nocturno 22:00 a 06:00
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Entra 22:05 del 10 de marzo, sale 06:02 del 11 de marzo
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 22, 5)),
        make_log(employee_pin, datetime(2026, 3, 11, 6, 2)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.PRESENT
    assert daily.date == date(2026, 3, 10)
    assert daily.first_check_in == datetime(2026, 3, 10, 22, 5)
    assert daily.last_check_out == datetime(2026, 3, 11, 6, 2)
    assert daily.tardiness_minutes == 0  # 5 min <= 10 min tolerancia


def test_process_daily_attendance_rest_day():
    # Domingo (día libre según esquema laboral)
    target_date = date(2026, 3, 8)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
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
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.REST_DAY


def test_process_daily_attendance_batch_for_branch():
    target_date = date(2026, 3, 10)

    # 3 empleados en sucursal 10
    emp1 = Employee(
        id=1,
        pin="1001",
        first_name="Juan",
        paternal_last_name="Perez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        home_branch_id=10,
        active=True,
    )
    emp2 = Employee(
        id=2,
        pin="1002",
        first_name="Maria",
        paternal_last_name="Lopez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.FEMALE,
        department_id=1,
        home_branch_id=10,
        active=True,
    )
    emp_inactive = Employee(
        id=3,
        pin="1003",
        first_name="Pedro",
        paternal_last_name="Gomez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        home_branch_id=10,
        active=False,  # Inactivo
    )
    employee_repo = InMemoryEmployeeRepository([emp1, emp2, emp_inactive])

    # Asignaciones para emp1 y emp2
    asg1 = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1001",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    asg2 = EmployeeScheduleAssignment(
        id=2,
        employee_pin="1002",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([asg1, asg2])

    # emp1 checó puntual, emp2 no checó (falta)
    logs = [
        make_log("1001", datetime(2026, 3, 10, 8, 0)),
        make_log("1001", datetime(2026, 3, 10, 17, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    results = process_daily_attendance_batch(
        target_date=target_date,
        employee_repo=employee_repo,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        branch_id=10,
    )

    # Solo los 2 empleados activos se procesan
    assert len(results) == 2
    r_by_pin = {r.employee_pin: r for r in results}
    assert r_by_pin["1001"].status == AttendanceStatus.PRESENT
    assert r_by_pin["1002"].status == AttendanceStatus.ABSENT


def test_process_daily_attendance_split_shift_punctual():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,  # SPLIT_SHIFT: 09:00-14:00 y 16:00-20:00 (540 min total)
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # 4 marcaciones para cubrir ambos segmentos de trabajo
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 9, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 14, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 20, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.PRESENT
    assert daily.tardiness_minutes == 0
    assert daily.early_departure_minutes == 0
    assert daily.total_worked_minutes == 540
    assert len(daily.sessions) == 2
    assert daily.first_check_in == datetime(2026, 3, 10, 9, 0)
    assert daily.last_check_out == datetime(2026, 3, 10, 20, 0)


def test_process_daily_attendance_split_shift_tardiness():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Entró a las 09:25 (tolerancia de 10 min -> 25 min de retardo)
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 9, 25)),
        make_log(employee_pin, datetime(2026, 3, 10, 14, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 20, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.LATE
    assert daily.tardiness_minutes == 25
    assert daily.early_departure_minutes == 0


def test_process_daily_attendance_split_shift_early_departure():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Salió a las 19:30 en vez de las 20:00 en el segundo bloque
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 9, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 14, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 19, 30)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.EARLY_DEPARTURE
    assert daily.early_departure_minutes == 30
    assert daily.tardiness_minutes == 0


def test_process_daily_attendance_split_shift_overtime():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Salió a las 21:00 en vez de las 20:00 (1 hora extra)
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 9, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 14, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 21, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    overtime_policy = OvertimePolicy(
        id=1,
        name="Horas Extra 15m",
        overtime_allowed=True,
        rounding_method=RoundingMethod.ROUND_DOWN,
        rounding_interval_minutes=15,
    )

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        overtime_policy=overtime_policy,
    )

    assert daily.status == AttendanceStatus.PRESENT
    assert daily.total_worked_minutes == 600
    assert daily.overtime_minutes == 60


def test_process_daily_attendance_split_shift_unjustified_absence():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.ABSENT


def test_process_daily_attendance_split_shift_incomplete():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=3,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    # Solo checó el primer bloque completo y la entrada del segundo bloque
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 9, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 14, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 16, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    daily = process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    assert daily.status == AttendanceStatus.INCOMPLETE
    assert daily.has_open_sessions is True


def test_process_daily_attendance_marks_logs_as_processed():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 17, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    # Pre-condición: ambos logs son RAW
    assert len(attendance_repo.get_unprocessed_logs()) == 2

    # Ejecución con marcado automático de logs
    process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        mark_logs_processed=True,
    )

    # Post-condición: ya no hay logs crudos sin procesar
    assert len(attendance_repo.get_unprocessed_logs()) == 0
    for log in logs:
        assert log.id is not None
        persisted_log = attendance_repo.get_by_id(log.id)
        assert persisted_log is not None
        assert persisted_log.processing_status == LogStatus.PROCESSED
        assert persisted_log.inferred_type == "daily_attendance"


def test_process_daily_attendance_mark_logs_processed_false():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 17, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    process_daily_attendance(
        employee_pin=employee_pin,
        target_date=target_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        mark_logs_processed=False,
    )

    # Si mark_logs_processed=False, permanecen RAW
    assert len(attendance_repo.get_unprocessed_logs()) == 2


def test_process_employee_attendance_range_full_week():
    start_date = date(2026, 3, 9)  # Lunes
    end_date = date(2026, 3, 15)  # Domingo
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
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
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])

    overtime_policy = OvertimePolicy(
        id=1,
        name="OT 15m",
        overtime_allowed=True,
        rounding_method=RoundingMethod.ROUND_DOWN,
        rounding_interval_minutes=15,
    )

    logs = [
        # Lunes 9: Puntual
        make_log(employee_pin, datetime(2026, 3, 9, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 9, 17, 0)),
        # Martes 10: Retardo 25 min (08:25)
        make_log(employee_pin, datetime(2026, 3, 10, 8, 25)),
        make_log(employee_pin, datetime(2026, 3, 10, 17, 0)),
        # Miércoles 11: Sin marcaciones (Falta)
        # Jueves 12: Horas extras (sale 18:35 -> 90 min OT)
        make_log(employee_pin, datetime(2026, 3, 12, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 12, 18, 35)),
        # Viernes 13: Salida anticipada 30 min (sale 16:30)
        make_log(employee_pin, datetime(2026, 3, 13, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 13, 16, 30)),
        # Sábado 14 y Domingo 15: Descanso programado
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    results = process_employee_attendance_range(
        employee_pin=employee_pin,
        start_date=start_date,
        end_date=end_date,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
        overtime_policy=overtime_policy,
    )

    assert len(results) == 7
    status_by_date = {r.date: r.status for r in results}
    assert status_by_date[date(2026, 3, 9)] == AttendanceStatus.PRESENT
    assert status_by_date[date(2026, 3, 10)] == AttendanceStatus.LATE
    assert status_by_date[date(2026, 3, 11)] == AttendanceStatus.ABSENT
    assert status_by_date[date(2026, 3, 12)] == AttendanceStatus.PRESENT
    assert status_by_date[date(2026, 3, 13)] == AttendanceStatus.EARLY_DEPARTURE
    assert status_by_date[date(2026, 3, 14)] == AttendanceStatus.REST_DAY
    assert status_by_date[date(2026, 3, 15)] == AttendanceStatus.REST_DAY

    # Verificar métricas individuales
    r_jueves = next(r for r in results if r.date == date(2026, 3, 12))
    assert r_jueves.overtime_minutes == 90

    r_martes = next(r for r in results if r.date == date(2026, 3, 10))
    assert r_martes.tardiness_minutes == 25

    # Verificar consulta de persistencia con el nuevo contrato get_by_date_range
    persisted_range = daily_repo.get_by_date_range(employee_pin, start_date, end_date)
    assert len(persisted_range) == 7
    assert [p.date for p in persisted_range] == [r.date for r in results]


def test_process_employee_attendance_range_class_and_call():
    target_date = date(2026, 3, 10)
    employee_pin = "1001"

    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin=employee_pin,
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])
    logs = [
        make_log(employee_pin, datetime(2026, 3, 10, 8, 0)),
        make_log(employee_pin, datetime(2026, 3, 10, 17, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    # Usando la clase ProcessDailyAttendance e inyección
    daily_processor = ProcessDailyAttendance(
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    range_processor = ProcessEmployeeAttendanceRange(daily_processor=daily_processor)

    # Invocación como callable __call__
    results = range_processor(
        employee_pin=employee_pin,
        start_date=target_date,
        end_date=target_date,
    )

    assert len(results) == 1
    assert results[0].status == AttendanceStatus.PRESENT


def test_process_employee_attendance_range_invalid_dates_raises_error():
    assignment_repo = InMemoryScheduleAssignmentRepository([])
    attendance_repo = InMemoryAttendanceRepository([])
    daily_repo = InMemoryDailyAttendanceRepository()

    processor = ProcessEmployeeAttendanceRange(
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    import pytest

    with pytest.raises(ValueError, match="end_date no puede ser anterior"):
        processor.execute(
            employee_pin="1001",
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 10),
        )


def test_sync_state_repository_in_memory_contract():
    repo = InMemorySyncStateRepository({1: 100})
    assert repo.get_last_synced_uid(1) == 100
    assert repo.get_last_synced_uid(2) == 0  # No configurado -> 0

    repo.update_last_synced_uid(2, 50)
    assert repo.get_last_synced_uid(2) == 50


def test_employee_repository_get_active_employees_contract():
    emp1 = Employee(
        id=1,
        pin="1001",
        first_name="Juan",
        paternal_last_name="Perez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        home_branch_id=10,
        active=True,
    )
    emp2 = Employee(
        id=2,
        pin="1002",
        first_name="Maria",
        paternal_last_name="Lopez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.FEMALE,
        department_id=1,
        home_branch_id=20,
        active=True,
    )
    emp3 = Employee(
        id=3,
        pin="1003",
        first_name="Pedro",
        paternal_last_name="Gomez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        home_branch_id=10,
        active=False,
    )
    repo = InMemoryEmployeeRepository([emp1, emp2, emp3])

    # Todos los activos
    active = repo.get_active_employees()
    assert len(active) == 2
    assert {e.pin for e in active} == {"1001", "1002"}

    # Activos de la sucursal 10
    branch_10_active = repo.get_active_employees(branch_id=10)
    assert len(branch_10_active) == 1
    assert branch_10_active[0].pin == "1001"


def test_process_daily_attendance_batch_class():
    target_date = date(2026, 3, 10)
    emp = Employee(
        id=1,
        pin="1001",
        first_name="Juan",
        paternal_last_name="Perez",
        maternal_last_name=None,
        hire_date=date(2025, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        home_branch_id=10,
        active=True,
    )
    employee_repo = InMemoryEmployeeRepository([emp])
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1001",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    assignment_repo = InMemoryScheduleAssignmentRepository([assignment])
    logs = [
        make_log("1001", datetime(2026, 3, 10, 8, 0)),
        make_log("1001", datetime(2026, 3, 10, 17, 0)),
    ]
    attendance_repo = InMemoryAttendanceRepository(logs)
    daily_repo = InMemoryDailyAttendanceRepository()

    batch_processor = ProcessDailyAttendanceBatch(
        employee_repo=employee_repo,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_repo,
        schedule_assignment_repo=assignment_repo,
        shift_definitions=SHIFT_DEFS,
        rotation_patterns={},
    )

    results = batch_processor(target_date=target_date)
    assert len(results) == 1
    assert results[0].status == AttendanceStatus.PRESENT

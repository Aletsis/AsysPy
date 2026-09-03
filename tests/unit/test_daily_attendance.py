"""Pruebas unitarias para DailyAttendance y AttendanceEvaluator."""

from datetime import date, datetime, time

from attendance.domain.attendance import (
    AttendanceEvaluator,
    AttendanceStatus,
    SessionStatus,
    SessionType,
    WorkSession,
)
from attendance.domain.policy import OvertimePolicy, RoundingMethod
from attendance.domain.schedule import (
    ScheduleKind,
    ScheduleResolution,
    ShiftCategory,
    ShiftDefinition,
    ShiftSegment,
)


def make_session(
    in_hour: int,
    in_minute: int,
    out_hour: int | None = None,
    out_minute: int = 0,
    base_date: date = date(2026, 3, 10),
    out_date: date | None = None,
    session_type: SessionType = SessionType.REGULAR_WORK,
) -> WorkSession:
    out_d = out_date or base_date
    return WorkSession(
        id=None,
        employee_pin="1001",
        check_in=datetime(base_date.year, base_date.month, base_date.day, in_hour, in_minute),
        check_out=datetime(out_d.year, out_d.month, out_d.day, out_hour, out_minute)
        if out_hour is not None
        else None,
        session_type=session_type,
        status=SessionStatus.CLOSED if out_hour is not None else SessionStatus.OPEN,
    )


REGULAR_SHIFT = ShiftDefinition(
    id=1,
    name="Turno 8 a 17",
    category=ShiftCategory.MATUTINO,
    start_time=time(8, 0),
    end_time=time(17, 0),
    tolerance_minutes=10,
)


def test_punctual_day_without_overtime():
    sessions = [make_session(7, 58, 17, 2)]
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=sessions,
    )

    assert daily.status == AttendanceStatus.PRESENT
    assert daily.tardiness_minutes == 0
    assert daily.early_departure_minutes == 0
    assert daily.total_worked_minutes == 544  # 9h y 4m
    assert daily.first_check_in == datetime(2026, 3, 10, 7, 58)
    assert daily.last_check_out == datetime(2026, 3, 10, 17, 2)


def test_tardiness_beyond_tolerance():
    # Entró a las 08:15 (tolerancia era 10 min) -> 15 min de retardo
    sessions = [make_session(8, 15, 17, 0)]
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=sessions,
    )

    assert daily.status == AttendanceStatus.LATE
    assert daily.tardiness_minutes == 15
    assert daily.early_departure_minutes == 0


def test_early_departure():
    # Salió a las 16:30 en lugar de las 17:00 -> 30 min de salida anticipada
    sessions = [make_session(8, 0, 16, 30)]
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=sessions,
    )

    assert daily.status == AttendanceStatus.EARLY_DEPARTURE
    assert daily.tardiness_minutes == 0
    assert daily.early_departure_minutes == 30


def test_incomplete_open_session():
    # Solo checó entrada a las 08:00
    sessions = [make_session(8, 0, None)]
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=sessions,
    )

    assert daily.status == AttendanceStatus.INCOMPLETE
    assert daily.has_open_sessions


def test_unjustified_absence():
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=[],
    )

    assert daily.status == AttendanceStatus.ABSENT


def test_justified_absence():
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=REGULAR_SHIFT)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=[],
        justified_absence_reason="Incapacidad médica IMSS",
    )

    assert daily.status == AttendanceStatus.JUSTIFIED_ABSENCE
    assert daily.notes == "Incapacidad médica IMSS"


def test_rest_day():
    resolution = ScheduleResolution(kind=ScheduleKind.OFF)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 15),
        resolution=resolution,
        sessions=[],
    )

    assert daily.status == AttendanceStatus.REST_DAY


def test_night_shift_crosses_midnight_anchored_to_start_date():
    # Turno 22:00 a 06:00 del día siguiente
    night_shift = ShiftDefinition(
        id=5,
        name="Turno Nocturno",
        category=ShiftCategory.NOCTURNO,
        start_time=time(22, 0),
        end_time=time(6, 0),
        tolerance_minutes=10,
        crosses_midnight=True,
    )
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=night_shift)

    # Marcaciones: entra 22:05 (10 de marzo), sale 06:02 (11 de marzo)
    sessions = [
        make_session(
            22,
            5,
            6,
            2,
            base_date=date(2026, 3, 10),
            out_date=date(2026, 3, 11),
        )
    ]

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),  # Anclada a la fecha de inicio
        resolution=resolution,
        sessions=sessions,
    )

    assert daily.date == date(2026, 3, 10)
    assert daily.status == AttendanceStatus.PRESENT
    assert daily.tardiness_minutes == 0  # 5 min <= 10 min tolerancia
    assert daily.early_departure_minutes == 0
    assert daily.total_worked_minutes == 477  # 7 horas y 57 minutos


def test_split_shift_and_meal_break():
    # Turno partido: Mañana 08:00 a 13:00, Tarde 14:00 a 18:00 (Total 9 horas = 540 min)
    split_shift = ShiftDefinition(
        id=6,
        name="Turno Partido",
        segments=[
            ShiftSegment(start_time=time(8, 0), end_time=time(13, 0)),
            ShiftSegment(start_time=time(14, 0), end_time=time(18, 0)),
        ],
    )
    resolution = ScheduleResolution(kind=ScheduleKind.FIXED, shift_definition=split_shift)

    # Dos sesiones de trabajo y una sesión de comida
    session1 = make_session(8, 0, 13, 0, session_type=SessionType.SPLIT_SHIFT_PART)
    lunch_break = make_session(13, 0, 14, 0, session_type=SessionType.MEAL_BREAK)
    session2 = make_session(14, 0, 18, 0, session_type=SessionType.SPLIT_SHIFT_PART)

    daily = AttendanceEvaluator.evaluate_day(
        employee_pin="1001",
        target_date=date(2026, 3, 10),
        resolution=resolution,
        sessions=[session1, lunch_break, session2],
    )

    assert daily.total_worked_minutes == 540  # 300 min + 240 min
    assert daily.total_break_minutes == 60  # 60 min de comida
    assert daily.status == AttendanceStatus.PRESENT


def test_overtime_policy_rounding_and_caps():
    policy = OvertimePolicy(
        id=1,
        name="Horas Extra 15m Round Down",
        overtime_allowed=True,
        rounding_method=RoundingMethod.ROUND_DOWN,
        rounding_interval_minutes=15,
        daily_cap_minutes=120,  # Máximo 2 horas
    )

    # 44 minutos de tiempo extra crudo -> 30 minutos con ROUND_DOWN a 15
    assert policy.calculate_effective_overtime(44) == 30

    # 150 minutos -> tope diario de 120
    assert policy.calculate_effective_overtime(150) == 120

    # NEAREST
    nearest_policy = OvertimePolicy(
        id=2,
        name="Nearest",
        rounding_method=RoundingMethod.NEAREST,
        rounding_interval_minutes=15,
    )
    assert (
        nearest_policy.calculate_effective_overtime(23) == 30
    )  # 23 está a más de la mitad (7.5) de 15
    assert nearest_policy.calculate_effective_overtime(21) == 15  # 21 está a menos de 7.5 sobre 15

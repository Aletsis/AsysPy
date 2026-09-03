from datetime import datetime

from attendance.application.attendance import pair_attendance_logs
from attendance.domain.attendance import SessionStatus
from attendance.domain.device import AttendanceLog, AuthMethod, LogStatus


def make_log(id: int, hour: int, minute: int = 0, device_id: int = 1) -> AttendanceLog:
    return AttendanceLog(
        id=id,
        record_uid=id,
        employee_pin="1965",
        device_id=device_id,
        timestamp=datetime(2026, 3, 10, hour, minute),
        raw_status=0,
        raw_punch=1,
        auth_method=AuthMethod.FINGERPRINT,
        processing_status=LogStatus.RAW,
    )


def test_simple_in_out_pair():
    logs = [make_log(1, 8, 0), make_log(2, 17, 0)]

    sessions = pair_attendance_logs("1965", logs)

    assert len(sessions) == 1
    assert sessions[0].status == SessionStatus.CLOSED
    assert sessions[0].check_in.hour == 8
    assert sessions[0].check_out is not None and sessions[0].check_out.hour == 17


def test_meal_break_produces_two_sessions():
    logs = [make_log(1, 8, 0), make_log(2, 13, 0), make_log(3, 14, 0), make_log(4, 17, 0)]

    sessions = pair_attendance_logs("1965", logs)

    assert len(sessions) == 2
    assert (
        sessions[0].check_in.hour == 8
        and sessions[0].check_out is not None
        and sessions[0].check_out.hour == 13
    )
    assert (
        sessions[1].check_in.hour == 14
        and sessions[1].check_out is not None
        and sessions[1].check_out.hour == 17
    )


def test_odd_trailing_log_is_open_not_closed():
    logs = [make_log(1, 8, 0), make_log(2, 17, 0), make_log(3, 22, 0)]

    sessions = pair_attendance_logs("1965", logs)

    assert len(sessions) == 2
    assert sessions[0].status == SessionStatus.CLOSED
    assert sessions[1].status == SessionStatus.OPEN
    assert sessions[1].check_out is None


def test_duplicate_punch_within_window_is_deduplicated():
    logs = [
        make_log(1, 8, 0),
        make_log(2, 8, 1),  # 1 minuto después — doble toque por error
        make_log(3, 17, 0),
    ]

    sessions = pair_attendance_logs("1965", logs)

    assert len(sessions) == 1
    assert sessions[0].check_in.hour == 8 and sessions[0].check_in.minute == 0
    assert sessions[0].check_out is not None and sessions[0].check_out.hour == 17


def test_cross_branch_session_keeps_both_device_ids():
    logs = [make_log(1, 8, 0, device_id=10), make_log(2, 17, 0, device_id=20)]

    sessions = pair_attendance_logs("1965", logs)

    assert sessions[0].check_in_device_id == 10
    assert sessions[0].check_out_device_id == 20


def test_empty_logs_returns_no_sessions():
    sessions = pair_attendance_logs("1965", [])

    assert sessions == []

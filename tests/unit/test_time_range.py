"""Pruebas unitarias para el Value Object TimeRange."""

from datetime import date, datetime, time

import pytest

from attendance.domain.common.exceptions import TimeRangeError
from attendance.domain.common.time_range import TimeRange


def test_daytime_range_duration_and_datetimes():
    tr = TimeRange(start_time=time(8, 0), end_time=time(17, 0))

    assert tr.duration_minutes == 9 * 60  # 540 minutos
    assert not tr.crosses_midnight

    start_dt, end_dt = tr.to_datetimes(date(2026, 3, 10))
    assert start_dt == datetime(2026, 3, 10, 8, 0)
    assert end_dt == datetime(2026, 3, 10, 17, 0)


def test_night_shift_crosses_midnight_duration_and_datetimes():
    # 22:00 a 06:00 (8 horas)
    tr = TimeRange(start_time=time(22, 0), end_time=time(6, 0))

    assert tr.crosses_midnight
    assert tr.duration_minutes == 8 * 60  # 480 minutos

    start_dt, end_dt = tr.to_datetimes(date(2026, 3, 10))
    assert start_dt == datetime(2026, 3, 10, 22, 0)
    assert end_dt == datetime(2026, 3, 11, 6, 0)  # pasa al día siguiente


def test_contains_datetime():
    tr = TimeRange(start_time=time(22, 0), end_time=time(6, 0))
    base_date = date(2026, 3, 10)

    # Marcación a las 23:30 del día de inicio
    assert tr.contains_datetime(datetime(2026, 3, 10, 23, 30), base_date)
    # Marcación a las 02:00 de la madrugada del día siguiente
    assert tr.contains_datetime(datetime(2026, 3, 11, 2, 0), base_date)
    # Fuera de rango
    assert not tr.contains_datetime(datetime(2026, 3, 10, 18, 0), base_date)
    assert not tr.contains_datetime(datetime(2026, 3, 11, 7, 0), base_date)


def test_identical_start_and_end_raises_error():
    with pytest.raises(TimeRangeError, match="no pueden ser idénticas"):
        TimeRange(start_time=time(8, 0), end_time=time(8, 0))


def test_inconsistent_crosses_midnight_flag():
    with pytest.raises(TimeRangeError, match="crosses_midnight es True"):
        TimeRange(start_time=time(8, 0), end_time=time(17, 0), crosses_midnight=True)

"""Pruebas unitarias para ShiftDefinition y RotationPattern."""

from datetime import date, time

import pytest

from attendance.domain.common.exceptions import ShiftValidationError
from attendance.domain.schedule import (
    RotationFrequency,
    RotationPattern,
    ShiftCategory,
    ShiftDefinition,
    ShiftSegment,
)


def test_shift_definition_continuous():
    shift = ShiftDefinition(
        id=1,
        name="Matutino",
        category=ShiftCategory.MATUTINO,
        start_time=time(8, 0),
        end_time=time(16, 0),
        tolerance_minutes=15,
    )

    assert not shift.is_split
    assert shift.expected_work_minutes == 480  # 8 horas
    assert shift.tolerance_minutes == 15
    # Llegada 08:10 (dentro de tolerancia)
    assert shift.calculate_first_segment_tardiness(time(8, 10)) == 0
    # Llegada 08:20 (retraso de 20 minutos)
    assert shift.calculate_first_segment_tardiness(time(8, 20)) == 20


def test_shift_definition_split():
    # Turno partido: Mañana 09:00 a 14:00 y Tarde 16:00 a 19:00
    seg1 = ShiftSegment(
        start_time=time(9, 0), end_time=time(14, 0), tolerance_minutes=10, name="Mañana"
    )
    seg2 = ShiftSegment(
        start_time=time(16, 0), end_time=time(19, 0), tolerance_minutes=5, name="Tarde"
    )

    split_shift = ShiftDefinition(
        id=2,
        name="Comercio Partido",
        category=ShiftCategory.MIXTO,
        segments=[seg1, seg2],
    )

    assert split_shift.is_split
    assert split_shift.start_time == time(9, 0)
    assert split_shift.end_time == time(19, 0)
    # 5 horas + 3 horas = 8 horas = 480 minutos
    assert split_shift.expected_work_minutes == 480
    assert split_shift.tolerance_minutes == 10
    assert split_shift.calculate_first_segment_tardiness(time(9, 5)) == 0
    assert split_shift.calculate_first_segment_tardiness(time(9, 15)) == 15


def test_negative_tolerance_raises_error():
    with pytest.raises(ShiftValidationError, match="negativa"):
        ShiftDefinition(
            id=3,
            name="Error",
            start_time=time(8, 0),
            end_time=time(17, 0),
            tolerance_minutes=-5,
        )


def test_rotation_pattern_daily_resolution():
    # Rotación 6x1 (6 días de trabajo, 1 de descanso)
    pattern = RotationPattern(
        id=1,
        name="6x1",
        shift_sequence=[1, 1, 1, 1, 1, 1, None],
        frequency=RotationFrequency.DAILY,
        anchor_date=date(2026, 1, 1),
    )

    # Día 1 a 6: turno 1
    assert pattern.resolve_shift_id(date(2026, 1, 1)) == 1
    assert pattern.resolve_shift_id(date(2026, 1, 6)) == 1
    # Día 7: descanso
    assert pattern.resolve_shift_id(date(2026, 1, 7)) is None
    # Día 8: vuelve a empezar turno 1
    assert pattern.resolve_shift_id(date(2026, 1, 8)) == 1

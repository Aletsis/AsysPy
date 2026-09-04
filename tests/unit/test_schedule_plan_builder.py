"""Pruebas unitarias para SchedulePlanBuilder."""

from datetime import date, time

import pytest

from attendance.application.schedule.plan_builder import (
    RestModeOption,
    SchedulePlanBuilder,
    SchedulePlanConfig,
    ShiftModeOption,
)
from attendance.domain.attendance.enums import AttendanceStatus
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.schedule.enums import AssignmentMode, RotationFrequency, Weekday
from attendance.domain.schedule.resolver import ScheduleKind, ScheduleResolver
from attendance.domain.schedule.shift import ShiftDefinition


@pytest.fixture
def sample_shifts() -> dict[int, ShiftDefinition]:
    return {
        1: ShiftDefinition(
            id=1,
            name="Matutino 08:00 - 16:00",
            start_time=time(8, 0),
            end_time=time(16, 0),
            tolerance_minutes=15,
        ),
        2: ShiftDefinition(
            id=2,
            name="Vespertino 14:00 - 22:00",
            start_time=time(14, 0),
            end_time=time(22, 0),
            tolerance_minutes=15,
        ),
    }


def test_fixed_shift_and_fixed_rest(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica configuración de Turno Fijo con Descanso Fijo semanal."""
    config = SchedulePlanConfig(
        employee_pin="E101",
        valid_from=date(2026, 3, 2),  # Lunes
        shift_mode=ShiftModeOption.FIXED,
        fixed_shift_id=1,
        rest_mode=RestModeOption.FIXED,
        fixed_rest_weekdays={6},  # Domingo
    )

    assign, pattern = SchedulePlanBuilder.build_assignment_and_pattern(config, sample_shifts)
    assert assign.mode == AssignmentMode.FIXED
    assert assign.shift_definition_id == 1
    assert pattern is None
    assert assign.working_weekdays == {
        Weekday.MONDAY,
        Weekday.TUESDAY,
        Weekday.WEDNESDAY,
        Weekday.THURSDAY,
        Weekday.FRIDAY,
        Weekday.SATURDAY,
    }

    preview = SchedulePlanBuilder.generate_preview(config, sample_shifts, days=14)
    assert len(preview) == 14
    # Domingo 2026-03-08 (índice 6) debe ser descanso
    assert preview[6].is_rest_day is True
    assert preview[6].shift_name == "Descanso"
    # Lunes 2026-03-02 (índice 0) debe ser laborable
    assert preview[0].is_rest_day is False
    assert preview[0].shift_name == "Matutino 08:00 - 16:00"


def test_fixed_shift_and_rolling_rest_day(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica descanso rotativo que se recorre al siguiente día cada semana."""
    config = SchedulePlanConfig(
        employee_pin="E102",
        valid_from=date(2026, 3, 2),  # Lunes de inicio
        shift_mode=ShiftModeOption.FIXED,
        fixed_shift_id=1,
        rest_mode=RestModeOption.ROLLING,
        rolling_initial_weekday=6,  # Semana 1 descansa Domingo
        rolling_interval_weeks=1,   # Se recorre cada semana
        rolling_step_days=1,        # +1 día hacia adelante (Dom -> Lun -> Mar...)
    )

    assign, pattern = SchedulePlanBuilder.build_assignment_and_pattern(config, sample_shifts)
    assert assign.mode == AssignmentMode.ROTATING
    assert pattern is not None
    assert pattern.frequency == RotationFrequency.DAILY
    assert len(pattern.shift_sequence) == 49  # 7 semanas * 7 días = 49 días

    # Previsualización de 21 días (3 semanas)
    preview = SchedulePlanBuilder.generate_preview(config, sample_shifts, days=21)

    # Semana 1 (2026-03-02 al 2026-03-08): descansa Domingo 2026-03-08 (índice 6)
    assert preview[6].date == date(2026, 3, 8)
    assert preview[6].is_rest_day is True
    assert preview[0].is_rest_day is False  # Lunes 2 trabaja

    # Semana 2 (2026-03-09 al 2026-03-15): descanso se recorrió a Lunes 2026-03-09 (índice 7)
    assert preview[7].date == date(2026, 3, 9)
    assert preview[7].is_rest_day is True
    assert preview[13].is_rest_day is False  # Domingo 15 trabaja!

    # Semana 3 (2026-03-16 al 2026-03-22): descanso se recorrió a Martes 2026-03-17 (índice 15)
    assert preview[15].date == date(2026, 3, 17)
    assert preview[15].is_rest_day is True
    assert preview[14].is_rest_day is False  # Lunes 16 trabaja!

    # Comprobación de resolución mediante ScheduleResolver
    assign.rotation_pattern_id = 99
    res_sun_w1 = ScheduleResolver.resolve(
        "E102",
        date(2026, 3, 8),
        [],
        assign,
        sample_shifts,
        {99: pattern},
    )
    assert res_sun_w1.kind == ScheduleKind.OFF

    res_mon_w2 = ScheduleResolver.resolve(
        "E102",
        date(2026, 3, 9),
        [],
        assign,
        sample_shifts,
        {99: pattern},
    )
    assert res_mon_w2.kind == ScheduleKind.OFF

    res_tue_w2 = ScheduleResolver.resolve(
        "E102",
        date(2026, 3, 10),
        [],
        assign,
        sample_shifts,
        {99: pattern},
    )
    assert res_tue_w2.kind == ScheduleKind.FIXED
    assert res_tue_w2.shift_definition is not None
    assert res_tue_w2.shift_definition.id == 1


def test_rotating_shifts_and_fixed_rest(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica turnos rotativos semanales (Turno 1 y 2) con descanso fijo en Domingo."""
    config = SchedulePlanConfig(
        employee_pin="E103",
        valid_from=date(2026, 3, 2),  # Lunes
        shift_mode=ShiftModeOption.ROTATING,
        rotating_shift_ids=[1, 2],    # Semana 1 turno 1, Semana 2 turno 2
        shift_frequency_weeks=1,
        rest_mode=RestModeOption.FIXED,
        fixed_rest_weekdays={6},      # Domingo siempre descanso
    )

    assign, pattern = SchedulePlanBuilder.build_assignment_and_pattern(config, sample_shifts)
    assert assign.mode == AssignmentMode.ROTATING
    assert pattern is not None
    # 2 turnos * 1 semana = 2 semanas = 14 días
    assert len(pattern.shift_sequence) == 14

    preview = SchedulePlanBuilder.generate_preview(config, sample_shifts, days=14)
    # Semana 1 (días 0..5): Turno 1
    assert preview[0].shift_id == 1
    assert preview[5].shift_id == 1
    assert preview[6].is_rest_day is True

    # Semana 2 (días 7..12): Turno 2
    assert preview[7].shift_id == 2
    assert preview[12].shift_id == 2
    assert preview[13].is_rest_day is True


def test_alternating_rest_days(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica descanso alternado (Semana 1: Domingo, Semana 2: Sábado)."""
    config = SchedulePlanConfig(
        employee_pin="E104",
        valid_from=date(2026, 3, 2),  # Lunes
        shift_mode=ShiftModeOption.FIXED,
        fixed_shift_id=1,
        rest_mode=RestModeOption.ALTERNATING,
        alternating_rest_weekdays=[6, 5],  # Semana 1 Domingo(6), Semana 2 Sábado(5)
        alternating_interval_weeks=1,
    )

    preview = SchedulePlanBuilder.generate_preview(config, sample_shifts, days=14)
    # Semana 1: Domingo 8 es descanso
    assert preview[6].date == date(2026, 3, 8)
    assert preview[6].is_rest_day is True

    # Semana 2: Sábado 14 es descanso, Domingo 15 laborable
    assert preview[12].date == date(2026, 3, 14)
    assert preview[12].is_rest_day is True
    assert preview[13].date == date(2026, 3, 15)
    assert preview[13].is_rest_day is False


def test_work_rest_cycle_continuous(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica ciclo continuo 4x2 (4 días trabajo x 2 descanso)."""
    config = SchedulePlanConfig(
        employee_pin="E105",
        valid_from=date(2026, 3, 1),
        shift_mode=ShiftModeOption.FIXED,
        fixed_shift_id=1,
        rest_mode=RestModeOption.WORK_REST_CYCLE,
        cycle_work_days=4,
        cycle_rest_days=2,
    )

    assign, pattern = SchedulePlanBuilder.build_assignment_and_pattern(config, sample_shifts)
    assert pattern is not None
    assert len(pattern.shift_sequence) == 6
    assert pattern.shift_sequence == [1, 1, 1, 1, None, None]

    preview = SchedulePlanBuilder.generate_preview(config, sample_shifts, days=6)
    assert [p.is_rest_day for p in preview] == [False, False, False, False, True, True]


def test_validation_errors(sample_shifts: dict[int, ShiftDefinition]) -> None:
    """Verifica validaciones de parámetros de configuración erróneos."""
    # PIN vacío
    with pytest.raises(ValidationError, match="Debe especificar el colaborador"):
        SchedulePlanBuilder.validate_config(
            SchedulePlanConfig(employee_pin="", valid_from=date(2026, 3, 1)),
            sample_shifts,
        )

    # Fecha fin anterior a inicio
    with pytest.raises(ValidationError, match="fecha de fin no puede ser anterior"):
        SchedulePlanBuilder.validate_config(
            SchedulePlanConfig(
                employee_pin="E1",
                valid_from=date(2026, 3, 10),
                valid_until=date(2026, 3, 5),
                fixed_shift_id=1,
                fixed_rest_weekdays={6},
            ),
            sample_shifts,
        )

    # Todos los días como descanso
    with pytest.raises(ValidationError, match="No se pueden marcar los 7 días"):
        SchedulePlanBuilder.validate_config(
            SchedulePlanConfig(
                employee_pin="E1",
                valid_from=date(2026, 3, 1),
                fixed_shift_id=1,
                fixed_rest_weekdays={0, 1, 2, 3, 4, 5, 6},
            ),
            sample_shifts,
        )

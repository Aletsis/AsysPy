from datetime import date

from attendance.application.schedule import resolve_expected_shift
from attendance.domain.schedule import (
    AssignmentMode,
    EmployeeScheduleAssignment,
    RotationFrequency,
    RotationPattern,
    ScheduleException,
    ScheduleKind,
    ShiftCategory,
    ShiftDefinition,
    Weekday,
)


class FakeAssignmentRepository:
    def __init__(self, assignment: EmployeeScheduleAssignment | None = None):
        self._assignment = assignment
        self.closed: list[tuple[int, date]] = []

    def get_active_assignment(self, employee_pin, as_of):
        return self._assignment

    def close_assignment(self, assignment_id, valid_until):
        self.closed.append((assignment_id, valid_until))

    def save(self, assignment):
        return assignment


MATUTINO = ShiftDefinition(
    id=1,
    name="Matutino",
    category=ShiftCategory.MATUTINO,
    start_time=None,
    end_time=None,
    tolerance_minutes=10,
    crosses_midnight=False,
)
VESPERTINO = ShiftDefinition(
    id=2,
    name="Vespertino",
    category=ShiftCategory.VESPERTINO,
    start_time=None,
    end_time=None,
    tolerance_minutes=10,
    crosses_midnight=False,
)
SHIFT_DEFS = {1: MATUTINO, 2: VESPERTINO}


def test_exception_forces_off_even_with_active_assignment():
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    exceptions = [
        ScheduleException(employee_pin="1965", date=date(2026, 3, 10), shift_definition_id=None)
    ]

    result = resolve_expected_shift(
        "1965",
        date(2026, 3, 10),
        exceptions,
        FakeAssignmentRepository(assignment),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.OFF


def test_exception_forces_specific_shift():
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )
    exceptions = [
        ScheduleException(employee_pin="1965", date=date(2026, 3, 10), shift_definition_id=2)
    ]

    result = resolve_expected_shift(
        "1965",
        date(2026, 3, 10),
        exceptions,
        FakeAssignmentRepository(assignment),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.FIXED
    assert result.shift_definition == VESPERTINO


def test_no_active_assignment_is_off():
    result = resolve_expected_shift(
        "1965",
        date(2026, 3, 10),
        [],
        FakeAssignmentRepository(None),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.OFF


def test_weekly_rest_day_is_off():
    # martes 10 de marzo 2026 - confirmamos que sea el weekday correcto
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
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
    sunday = date(2026, 3, 8)  # domingo

    result = resolve_expected_shift(
        "1965",
        sunday,
        [],
        FakeAssignmentRepository(assignment),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.OFF


def test_fixed_assignment_returns_its_shift():
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 1, 1),
        shift_definition_id=1,
    )

    result = resolve_expected_shift(
        "1965",
        date(2026, 3, 10),
        [],
        FakeAssignmentRepository(assignment),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.FIXED
    assert result.shift_definition == MATUTINO


def test_open_assignment_returns_open():
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.OPEN,
        valid_from=date(2026, 1, 1),
    )

    result = resolve_expected_shift(
        "1965",
        date(2026, 3, 10),
        [],
        FakeAssignmentRepository(assignment),
        SHIFT_DEFS,
        {},
    )

    assert result.kind == ScheduleKind.OPEN
    assert result.shift_definition is None


def test_rotating_weekly_alternates_between_shifts():
    pattern = RotationPattern(
        id=1,
        name="Rotación semanal",
        shift_sequence=[1, 2],
        frequency=RotationFrequency.WEEKLY,
        anchor_date=date(2026, 1, 5),  # lunes
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2026, 1, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    week_0 = resolve_expected_shift("1965", date(2026, 1, 6), [], repo, SHIFT_DEFS, {1: pattern})
    week_1 = resolve_expected_shift("1965", date(2026, 1, 13), [], repo, SHIFT_DEFS, {1: pattern})
    week_2 = resolve_expected_shift("1965", date(2026, 1, 20), [], repo, SHIFT_DEFS, {1: pattern})

    assert week_0.shift_definition == MATUTINO
    assert week_1.shift_definition == VESPERTINO
    assert week_2.shift_definition == MATUTINO  # vuelve a rotar


def test_rotation_rest_day_within_sequence_is_off():
    pattern = RotationPattern(
        id=1,
        name="6x1",
        shift_sequence=[1, 1, 1, 1, 1, 1, None],  # descansa cada 7º día
        frequency=RotationFrequency.DAILY,
        anchor_date=date(2026, 1, 1),
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2026, 1, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    rest_day = resolve_expected_shift("1965", date(2026, 1, 7), [], repo, SHIFT_DEFS, {1: pattern})
    work_day = resolve_expected_shift("1965", date(2026, 1, 6), [], repo, SHIFT_DEFS, {1: pattern})

    assert rest_day.kind == ScheduleKind.OFF
    assert work_day.kind == ScheduleKind.FIXED


def test_rotating_monthly_across_year_boundary():
    pattern = RotationPattern(
        id=1,
        name="Rotación mensual",
        shift_sequence=[1, 2],
        frequency=RotationFrequency.MONTHLY,
        anchor_date=date(2025, 12, 15),
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2025, 12, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    # mismo mes que el ancla, antes del día 15 → 0 meses transcurridos
    same_month_before_day = resolve_expected_shift(
        "1965", date(2026, 1, 10), [], repo, SHIFT_DEFS, {1: pattern}
    )
    # después del día 15 → 1 mes transcurrido
    same_month_after_day = resolve_expected_shift(
        "1965", date(2026, 1, 20), [], repo, SHIFT_DEFS, {1: pattern}
    )

    assert same_month_before_day.shift_definition == MATUTINO
    assert same_month_after_day.shift_definition == VESPERTINO


def test_monthly_rotation_with_day_31_anchor_stays_previous_period_through_february():
    # ancla el día 31 de enero — febrero nunca llega al día 31,
    # así que el período no debería cambiar durante todo febrero
    pattern = RotationPattern(
        id=1,
        name="Rotación mensual",
        shift_sequence=[1, 2],
        frequency=RotationFrequency.MONTHLY,
        anchor_date=date(2026, 1, 31),
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2026, 1, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    feb_1 = resolve_expected_shift("1965", date(2026, 2, 1), [], repo, SHIFT_DEFS, {1: pattern})
    feb_27 = resolve_expected_shift("1965", date(2026, 2, 27), [], repo, SHIFT_DEFS, {1: pattern})
    feb_28 = resolve_expected_shift(
        "1965", date(2026, 2, 28), [], repo, SHIFT_DEFS, {1: pattern}
    )  # último día, 2026 no es bisiesto

    assert feb_1.shift_definition == MATUTINO
    assert feb_27.shift_definition == MATUTINO
    assert (
        feb_28.shift_definition == MATUTINO
    )  # sigue en el período 0, "31 de febrero" nunca ocurre


def test_monthly_rotation_transitions_on_march_1_after_short_february():
    pattern = RotationPattern(
        id=1,
        name="Rotación mensual",
        shift_sequence=[1, 2],
        frequency=RotationFrequency.MONTHLY,
        anchor_date=date(2026, 1, 31),
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2026, 1, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    result = resolve_expected_shift("1965", date(2026, 3, 1), [], repo, SHIFT_DEFS, {1: pattern})

    assert result.shift_definition == VESPERTINO  # el período avanza aquí, no en febrero


def test_monthly_rotation_with_day_31_anchor_leap_year_february():
    # 2028 sí es bisiesto — el día 29 tampoco es 31, mismo comportamiento esperado
    pattern = RotationPattern(
        id=1,
        name="Rotación mensual",
        shift_sequence=[1, 2],
        frequency=RotationFrequency.MONTHLY,
        anchor_date=date(2028, 1, 31),
    )
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="1965",
        mode=AssignmentMode.ROTATING,
        valid_from=date(2028, 1, 1),
        rotation_pattern_id=1,
    )
    repo = FakeAssignmentRepository(assignment)

    feb_29 = resolve_expected_shift("1965", date(2028, 2, 29), [], repo, SHIFT_DEFS, {1: pattern})
    mar_1 = resolve_expected_shift("1965", date(2028, 3, 1), [], repo, SHIFT_DEFS, {1: pattern})

    assert feb_29.shift_definition == MATUTINO
    assert mar_1.shift_definition == VESPERTINO

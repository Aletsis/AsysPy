"""Puerto EmployeeScheduleAssignmentRepository para asignaciones de horario."""

from datetime import date
from typing import Protocol

from attendance.domain.schedule.assignment import EmployeeScheduleAssignment


class EmployeeScheduleAssignmentRepository(Protocol):
    def get_active_assignment(
        self, employee_pin: str, as_of: date
    ) -> EmployeeScheduleAssignment | None: ...

    def close_assignment(self, assignment_id: int, valid_until: date) -> None: ...

    def save(
        self, assignment: EmployeeScheduleAssignment
    ) -> EmployeeScheduleAssignment: ...

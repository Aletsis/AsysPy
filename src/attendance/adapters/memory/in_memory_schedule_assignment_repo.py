"""Adaptador en memoria para EmployeeScheduleAssignmentRepository."""

from datetime import date
from typing import Dict

from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.ports.schedule import (
    EmployeeScheduleAssignmentRepository,
)


class InMemoryScheduleAssignmentRepository(EmployeeScheduleAssignmentRepository):
    """Implementación en memoria para asignaciones de horario a empleados."""

    def __init__(
        self, initial_assignments: list[EmployeeScheduleAssignment] | None = None
    ) -> None:
        self._assignments: Dict[int, EmployeeScheduleAssignment] = {}
        self._next_id = 1
        if initial_assignments:
            for a in initial_assignments:
                self.save(a)

    def save(
        self, assignment: EmployeeScheduleAssignment
    ) -> EmployeeScheduleAssignment:
        if assignment.id is None:
            assignment.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, assignment.id + 1)
        self._assignments[assignment.id] = assignment
        return assignment

    def get_active_assignment(
        self, employee_pin: str, as_of: date
    ) -> EmployeeScheduleAssignment | None:
        for a in self._assignments.values():
            if a.employee_pin == employee_pin and a.is_active_on(as_of):
                return a
        return None

    def close_assignment(self, assignment_id: int, valid_until: date) -> None:
        if assignment_id in self._assignments:
            self._assignments[assignment_id].valid_until = valid_until

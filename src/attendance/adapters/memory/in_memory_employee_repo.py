"""Adaptador en memoria para EmployeeRepository."""

from typing import Dict

from attendance.domain.organization.employee import Employee
from attendance.ports.organization import EmployeeRepository


class InMemoryEmployeeRepository(EmployeeRepository):
    """Implementación en memoria para la gestión y consulta de empleados."""

    def __init__(self, initial_employees: list[Employee] | None = None) -> None:
        self._by_id: Dict[int, Employee] = {}
        self._by_pin: Dict[str, Employee] = {}
        self._next_id = 1
        if initial_employees:
            for emp in initial_employees:
                self.save(emp)

    def save(self, employee: Employee) -> Employee:
        if employee.id is None:
            employee.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, employee.id + 1)
        self._by_id[employee.id] = employee
        self._by_pin[employee.pin] = employee
        return employee

    def get_by_pin(self, pin: str) -> Employee | None:
        return self._by_pin.get(pin)

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self._by_id.get(employee_id)

    def list_active(self, branch_id: int | None = None) -> list[Employee]:
        emps = [emp for emp in self._by_id.values() if emp.active]
        if branch_id is not None:
            emps = [emp for emp in emps if emp.home_branch_id == branch_id]
        return emps

    def get_active_employees(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_active(branch_id=branch_id)

    def list_all(self, branch_id: int | None = None) -> list[Employee]:
        emps = list(self._by_id.values())
        if branch_id is not None:
            emps = [emp for emp in emps if emp.home_branch_id == branch_id]
        return emps

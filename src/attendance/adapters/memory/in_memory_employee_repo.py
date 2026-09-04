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

    def save_all(self, employees: list[Employee]) -> list[Employee]:
        return [self.save(emp) for emp in employees]

    def get_by_pin(self, pin: str) -> Employee | None:
        return self._by_pin.get(pin)

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self._by_id.get(employee_id)

    def get_by_curp(self, curp: str) -> Employee | None:
        cleaned = curp.strip().upper()
        if not cleaned:
            return None
        for emp in self._by_id.values():
            if emp.curp == cleaned:
                return emp
        return None

    def get_by_rfc(self, rfc: str) -> Employee | None:
        cleaned = rfc.strip().upper()
        if not cleaned:
            return None
        for emp in self._by_id.values():
            if emp.rfc == cleaned:
                return emp
        return None

    def get_by_card_number(self, card_number: str) -> Employee | None:
        cleaned = card_number.strip()
        if not cleaned:
            return None
        for emp in self._by_id.values():
            if emp.card_number == cleaned:
                return emp
        return None

    def get_by_email(self, email: str) -> Employee | None:
        cleaned = email.strip().lower()
        if not cleaned:
            return None
        for emp in self._by_id.values():
            if emp.email == cleaned:
                return emp
        return None

    def exists_by_pin(self, pin: str) -> bool:
        return pin in self._by_pin

    def exists_by_id(self, employee_id: int) -> bool:
        return employee_id in self._by_id

    def list_active(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_all(branch_id=branch_id, active_only=True)

    def get_active_employees(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_active(branch_id=branch_id)

    def list_all(
        self,
        branch_id: int | None = None,
        department_id: int | None = None,
        position_id: int | None = None,
        active_only: bool = False,
    ) -> list[Employee]:
        emps = list(self._by_id.values())
        if active_only:
            emps = [emp for emp in emps if emp.active]
        if branch_id is not None:
            emps = [emp for emp in emps if emp.home_branch_id == branch_id]
        if department_id is not None:
            emps = [emp for emp in emps if emp.department_id == department_id]
        if position_id is not None:
            emps = [emp for emp in emps if emp.position_id == position_id]
        return sorted(emps, key=lambda e: (e.paternal_last_name, e.first_name))

    def count(
        self,
        branch_id: int | None = None,
        department_id: int | None = None,
        position_id: int | None = None,
        active_only: bool = False,
    ) -> int:
        return len(
            self.list_all(
                branch_id=branch_id,
                department_id=department_id,
                position_id=position_id,
                active_only=active_only,
            )
        )

    def delete(self, pin: str) -> bool:
        if pin in self._by_pin:
            emp = self._by_pin.pop(pin)
            if emp.id is not None and emp.id in self._by_id:
                del self._by_id[emp.id]
            return True
        return False

    def delete_by_id(self, employee_id: int) -> bool:
        if employee_id in self._by_id:
            emp = self._by_id.pop(employee_id)
            if emp.pin in self._by_pin:
                del self._by_pin[emp.pin]
            return True
        return False

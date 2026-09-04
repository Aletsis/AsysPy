"""Adaptador en memoria para ScheduleExceptionRepository."""

from datetime import date
from typing import Dict

from attendance.domain.schedule.exception import ScheduleException
from attendance.ports.schedule.schedule_exception_repository import ScheduleExceptionRepository


class InMemoryScheduleExceptionRepository(ScheduleExceptionRepository):
    """Implementación en memoria para excepciones de horario individuales."""

    def __init__(
        self, initial_exceptions: list[ScheduleException] | None = None
    ) -> None:
        self._exceptions: Dict[int, ScheduleException] = {}
        self._next_id = 1
        if initial_exceptions:
            for exc in initial_exceptions:
                self.save(exc)

    def save(self, exception: ScheduleException) -> ScheduleException:
        if exception.id is None:
            # Si ya existe para el mismo empleado y fecha, actualizar
            for existing in self._exceptions.values():
                if (
                    existing.employee_pin == exception.employee_pin
                    and existing.date == exception.date
                ):
                    existing.shift_definition_id = exception.shift_definition_id
                    existing.reason = exception.reason
                    return existing

            exception.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, exception.id + 1)
        self._exceptions[exception.id] = exception
        return exception

    def get_by_id(self, exception_id: int) -> ScheduleException | None:
        return self._exceptions.get(exception_id)

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> ScheduleException | None:
        for exc in self._exceptions.values():
            if exc.employee_pin == employee_pin and exc.date == target_date:
                return exc
        return None

    def list_for_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ScheduleException]:
        results = [
            exc for exc in self._exceptions.values() if exc.employee_pin == employee_pin
        ]
        if start_date:
            results = [exc for exc in results if exc.date >= start_date]
        if end_date:
            results = [exc for exc in results if exc.date <= end_date]
        return sorted(results, key=lambda e: e.date)

    def list_for_date(self, target_date: date) -> list[ScheduleException]:
        return [exc for exc in self._exceptions.values() if exc.date == target_date]

    def list_all(self) -> list[ScheduleException]:
        return sorted(self._exceptions.values(), key=lambda e: e.date, reverse=True)

    def delete(self, exception_id: int) -> bool:
        if exception_id in self._exceptions:
            del self._exceptions[exception_id]
            return True
        return False

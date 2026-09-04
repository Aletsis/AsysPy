"""Puerto ScheduleExceptionRepository para excepciones y eventualidades de horario."""

from datetime import date
from typing import Protocol

from attendance.domain.schedule.exception import ScheduleException


class ScheduleExceptionRepository(Protocol):
    """Contrato de persistencia para excepciones de horario individuales."""

    def save(self, exception: ScheduleException) -> ScheduleException: ...

    def get_by_id(self, exception_id: int) -> ScheduleException | None: ...

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> ScheduleException | None: ...

    def list_for_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ScheduleException]: ...

    def list_for_date(self, target_date: date) -> list[ScheduleException]: ...

    def list_all(self) -> list[ScheduleException]: ...

    def delete(self, exception_id: int) -> bool: ...

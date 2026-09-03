"""Puerto DailyAttendanceRepository para jornadas diarias procesadas."""

from datetime import date
from typing import Protocol

from attendance.domain.attendance.daily_attendance import DailyAttendance


class DailyAttendanceRepository(Protocol):
    """Contrato de persistencia para jornadas diarias procesadas."""

    def save(self, daily_attendance: DailyAttendance) -> DailyAttendance: ...

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> DailyAttendance | None: ...

    def get_by_employee_and_date_range(
        self, employee_pin: str, start_date: date, end_date: date
    ) -> list[DailyAttendance]: ...

    def get_by_date_range(
        self, employee_pin: str, from_date: date, to_date: date
    ) -> list[DailyAttendance]: ...

    def list_by_date(
        self, target_date: date, branch_id: int | None = None
    ) -> list[DailyAttendance]: ...

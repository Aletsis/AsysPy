"""Adaptador en memoria para DailyAttendanceRepository."""

from datetime import date
from typing import Dict, Tuple

from attendance.domain.attendance.daily_attendance import DailyAttendance
from attendance.ports.attendance import DailyAttendanceRepository


class InMemoryDailyAttendanceRepository(DailyAttendanceRepository):
    """Implementación en memoria para jornadas diarias procesadas."""

    def __init__(self) -> None:
        # Clave primaria compuesta lógica: (employee_pin, date)
        self._records: Dict[Tuple[str, date], DailyAttendance] = {}

    def save(self, daily_attendance: DailyAttendance) -> DailyAttendance:
        key = (daily_attendance.employee_pin, daily_attendance.date)
        self._records[key] = daily_attendance
        return daily_attendance

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> DailyAttendance | None:
        return self._records.get((employee_pin, target_date))

    def get_by_employee_and_date_range(
        self, employee_pin: str, start_date: date, end_date: date
    ) -> list[DailyAttendance]:
        return sorted(
            [
                att
                for (pin, d), att in self._records.items()
                if pin == employee_pin and start_date <= d <= end_date
            ],
            key=lambda a: a.date,
        )

    def get_by_date_range(
        self, employee_pin: str, from_date: date, to_date: date
    ) -> list[DailyAttendance]:
        return self.get_by_employee_and_date_range(employee_pin, from_date, to_date)

    def list_by_date(
        self, target_date: date, branch_id: int | None = None
    ) -> list[DailyAttendance]:
        return [
            att for (pin, d), att in self._records.items() if d == target_date
        ]

    def list_all(self) -> list[DailyAttendance]:
        return sorted(self._records.values(), key=lambda a: (a.date, a.employee_pin))

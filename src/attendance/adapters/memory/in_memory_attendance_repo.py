"""Adaptador en memoria para AttendanceRepository."""

from datetime import date, datetime
from typing import Dict

from attendance.domain.device.enums import LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.ports.attendance import AttendanceRepository


class InMemoryAttendanceRepository(AttendanceRepository):
    """Implementación en memoria del repositorio de marcaciones para pruebas y desarrollo."""

    def __init__(self, initial_logs: list[AttendanceLog] | None = None) -> None:
        self._logs: Dict[int, AttendanceLog] = {}
        self._next_id = 1
        if initial_logs:
            for log in initial_logs:
                self.save_raw_log(log)

    def save_raw_log(self, log: AttendanceLog) -> None:
        if log.id is None:
            log.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, log.id + 1)
        self._logs[log.id] = log

    def get_unprocessed_logs(self) -> list[AttendanceLog]:
        return [
            log
            for log in self._logs.values()
            if log.processing_status == LogStatus.RAW
        ]

    def mark_as_processed(self, log_id: int, inferred_type: str) -> None:
        if log_id in self._logs:
            self._logs[log_id].mark_as_processed(inferred_type)

    def get_by_id(self, log_id: int) -> AttendanceLog | None:
        return self._logs.get(log_id)

    def get_logs_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> list[AttendanceLog]:
        return sorted(
            [
                log
                for log in self._logs.values()
                if log.employee_pin == employee_pin
                and log.timestamp.date() == target_date
                and log.processing_status != LogStatus.IGNORED
            ],
            key=lambda item: item.timestamp,
        )

    def get_logs_for_employee(
        self, employee_pin: str, start_time: datetime, end_time: datetime
    ) -> list[AttendanceLog]:
        return sorted(
            [
                log
                for log in self._logs.values()
                if log.employee_pin == employee_pin
                and start_time <= log.timestamp <= end_time
                and log.processing_status != LogStatus.IGNORED
            ],
            key=lambda item: item.timestamp,
        )

    def update_log(self, log: AttendanceLog) -> AttendanceLog:
        if log.id is None:
            self.save_raw_log(log)
        else:
            self._logs[log.id] = log
        return log

    def list_all(self) -> list[AttendanceLog]:
        return sorted(self._logs.values(), key=lambda item: item.timestamp)

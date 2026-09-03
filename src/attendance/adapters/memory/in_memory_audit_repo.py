"""Adaptador en memoria para AuditLogRepository."""

from typing import Dict

from attendance.domain.audit.audit_log import AuditLog
from attendance.ports.audit import AuditLogRepository


class InMemoryAuditLogRepository(AuditLogRepository):
    """Implementación en memoria para la trazabilidad de auditoría."""

    def __init__(self) -> None:
        self._logs: Dict[int, AuditLog] = {}
        self._next_id = 1

    def save(self, log: AuditLog) -> AuditLog:
        if log.id is None:
            log.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, log.id + 1)
        self._logs[log.id] = log
        return log

    def list_by_entity(self, entity_type: str, entity_id: str | int) -> list[AuditLog]:
        return [
            log
            for log in self._logs.values()
            if log.entity_type == entity_type and str(log.entity_id) == str(entity_id)
        ]

    def list_by_employee(self, employee_pin: str) -> list[AuditLog]:
        return [
            log
            for log in self._logs.values()
            if log.employee_pin == employee_pin
        ]

"""Puerto AuditLogRepository para trazabilidad de auditoría."""

from typing import Protocol

from attendance.domain.audit.audit_log import AuditLog


class AuditLogRepository(Protocol):
    """Contrato de persistencia para la trazabilidad de auditoría."""

    def save(self, log: AuditLog) -> AuditLog: ...

    def list_by_entity(self, entity_type: str, entity_id: str | int) -> list[AuditLog]: ...

    def list_by_employee(self, employee_pin: str) -> list[AuditLog]: ...

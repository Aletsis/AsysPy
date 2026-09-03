"""Adaptador SQLAlchemy para AuditLogRepository (Trazabilidad de auditoría)."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    audit_log_to_domain,
    audit_log_to_model,
)
from attendance.adapters.persistence.sql.models import AuditLogModel
from attendance.domain.audit.audit_log import AuditLog
from attendance.ports.audit import AuditLogRepository


class SqlAuditLogRepository(AuditLogRepository):
    """Implementación relacional del repositorio de auditoría inmutable."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, log: AuditLog) -> AuditLog:
        with self.session_factory() as session:
            model = audit_log_to_model(log)
            session.add(model)
            session.commit()
            log.id = model.id
            return audit_log_to_domain(model)

    def list_by_entity(self, entity_type: str, entity_id: str | int) -> list[AuditLog]:
        with self.session_factory() as session:
            stmt = (
                select(AuditLogModel)
                .where(
                    AuditLogModel.entity_type == entity_type,
                    AuditLogModel.entity_id == str(entity_id),
                )
                .order_by(AuditLogModel.timestamp.asc())
            )
            models = session.scalars(stmt).all()
            return [audit_log_to_domain(m) for m in models]

    def list_by_employee(self, employee_pin: str) -> list[AuditLog]:
        with self.session_factory() as session:
            stmt = (
                select(AuditLogModel)
                .where(AuditLogModel.employee_pin == employee_pin)
                .order_by(AuditLogModel.timestamp.asc())
            )
            models = session.scalars(stmt).all()
            return [audit_log_to_domain(m) for m in models]

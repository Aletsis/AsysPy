"""Adaptador SQLAlchemy para IncidenceRepository (Justificaciones e Incidencias)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    justification_to_domain,
    justification_to_model,
)
from attendance.adapters.persistence.sql.models import JustificationModel
from attendance.domain.incidence.enums import JustificationStatus
from attendance.domain.incidence.justification import Justification
from attendance.ports.incidence import IncidenceRepository


class SqlIncidenceRepository(IncidenceRepository):
    """Implementación relacional del repositorio de justificaciones e incidencias."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, justification: Justification) -> Justification:
        with self.session_factory() as session:
            if justification.id is not None:
                model = session.get(JustificationModel, justification.id)
                if model:
                    model.employee_pin = justification.employee_pin
                    model.type = justification.type.value
                    model.start_date = justification.start_date
                    model.end_date = justification.end_date
                    model.reason = justification.reason
                    model.approved_by = justification.approved_by
                    model.status = justification.status.value
                    model.support_document = justification.support_document
                    model.start_time = justification.start_time
                    model.end_time = justification.end_time
                    session.commit()
                    return justification_to_domain(model)

            new_model = justification_to_model(justification)
            session.add(new_model)
            session.commit()
            justification.id = new_model.id
            return justification_to_domain(new_model)

    def get_by_id(self, justification_id: int) -> Justification | None:
        with self.session_factory() as session:
            model = session.get(JustificationModel, justification_id)
            return justification_to_domain(model) if model else None

    def get_active_justification(
        self, employee_pin: str, target_date: date
    ) -> Justification | None:
        with self.session_factory() as session:
            stmt = (
                select(JustificationModel)
                .where(
                    JustificationModel.employee_pin == employee_pin,
                    JustificationModel.status == JustificationStatus.APPROVED.value,
                    JustificationModel.start_date <= target_date,
                    JustificationModel.end_date >= target_date,
                )
                .order_by(JustificationModel.created_at.desc())
            )
            model = session.scalars(stmt).first()
            return justification_to_domain(model) if model else None

    def list_by_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Justification]:
        with self.session_factory() as session:
            stmt = select(JustificationModel).where(JustificationModel.employee_pin == employee_pin)
            if start_date is not None:
                stmt = stmt.where(JustificationModel.end_date >= start_date)
            if end_date is not None:
                stmt = stmt.where(JustificationModel.start_date <= end_date)
            stmt = stmt.order_by(JustificationModel.start_date.asc())
            models = session.scalars(stmt).all()
            return [justification_to_domain(m) for m in models]

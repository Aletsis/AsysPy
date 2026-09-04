"""Adaptador SQLAlchemy para ScheduleExceptionRepository."""

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    schedule_exception_to_domain,
    schedule_exception_to_model,
)
from attendance.adapters.persistence.sql.models import ScheduleExceptionModel
from attendance.domain.schedule.exception import ScheduleException
from attendance.ports.schedule.schedule_exception_repository import ScheduleExceptionRepository


class SqlScheduleExceptionRepository(ScheduleExceptionRepository):
    """Implementación relacional del repositorio de excepciones de horario."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, exception: ScheduleException) -> ScheduleException:
        with self.session_factory() as session:
            if exception.id is not None:
                model = session.get(ScheduleExceptionModel, exception.id)
                if model:
                    model_data = schedule_exception_to_model(exception)
                    model.employee_pin = model_data.employee_pin
                    model.date = model_data.date
                    model.shift_definition_id = model_data.shift_definition_id
                    model.reason = model_data.reason
                    session.commit()
                    return schedule_exception_to_domain(model)

            # Verificar si ya existe una excepción para el mismo empleado y fecha
            stmt = select(ScheduleExceptionModel).where(
                and_(
                    ScheduleExceptionModel.employee_pin == exception.employee_pin,
                    ScheduleExceptionModel.date == exception.date,
                )
            )
            existing = session.scalars(stmt).first()
            if existing:
                existing.shift_definition_id = exception.shift_definition_id
                existing.reason = exception.reason
                session.commit()
                return schedule_exception_to_domain(existing)

            new_model = schedule_exception_to_model(exception)
            session.add(new_model)
            session.commit()
            exception.id = new_model.id
            return schedule_exception_to_domain(new_model)

    def get_by_id(self, exception_id: int) -> ScheduleException | None:
        with self.session_factory() as session:
            model = session.get(ScheduleExceptionModel, exception_id)
            return schedule_exception_to_domain(model) if model else None

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> ScheduleException | None:
        with self.session_factory() as session:
            stmt = select(ScheduleExceptionModel).where(
                and_(
                    ScheduleExceptionModel.employee_pin == employee_pin,
                    ScheduleExceptionModel.date == target_date,
                )
            )
            model = session.scalars(stmt).first()
            return schedule_exception_to_domain(model) if model else None

    def list_for_employee(
        self,
        employee_pin: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ScheduleException]:
        with self.session_factory() as session:
            conditions = [ScheduleExceptionModel.employee_pin == employee_pin]
            if start_date:
                conditions.append(ScheduleExceptionModel.date >= start_date)
            if end_date:
                conditions.append(ScheduleExceptionModel.date <= end_date)
            stmt = (
                select(ScheduleExceptionModel)
                .where(and_(*conditions))
                .order_by(ScheduleExceptionModel.date)
            )
            models = session.scalars(stmt).all()
            return [schedule_exception_to_domain(m) for m in models]

    def list_for_date(self, target_date: date) -> list[ScheduleException]:
        with self.session_factory() as session:
            stmt = select(ScheduleExceptionModel).where(
                ScheduleExceptionModel.date == target_date
            )
            models = session.scalars(stmt).all()
            return [schedule_exception_to_domain(m) for m in models]

    def list_all(self) -> list[ScheduleException]:
        with self.session_factory() as session:
            stmt = select(ScheduleExceptionModel).order_by(
                ScheduleExceptionModel.date.desc(), ScheduleExceptionModel.id.desc()
            )
            models = session.scalars(stmt).all()
            return [schedule_exception_to_domain(m) for m in models]

    def delete(self, exception_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(ScheduleExceptionModel, exception_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

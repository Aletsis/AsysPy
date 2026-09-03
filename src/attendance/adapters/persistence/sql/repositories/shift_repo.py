"""Adaptador SQLAlchemy para ShiftRepository."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    shift_to_domain,
    shift_to_model,
)
from attendance.adapters.persistence.sql.models import ShiftModel
from attendance.domain.schedule.shift import ShiftDefinition
from attendance.ports.schedule.shift_repository import ShiftRepository


class SqlShiftRepository(ShiftRepository):
    """Implementación relacional del repositorio del catálogo de turnos."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, shift: ShiftDefinition) -> ShiftDefinition:
        with self.session_factory() as session:
            if shift.id is not None:
                model = session.get(ShiftModel, shift.id)
                if model:
                    model_data = shift_to_model(shift)
                    model.name = model_data.name
                    model.category = model_data.category
                    model.start_time = model_data.start_time
                    model.end_time = model_data.end_time
                    model.tolerance_minutes = model_data.tolerance_minutes
                    model.crosses_midnight = model_data.crosses_midnight
                    model.segments = model_data.segments
                    session.commit()
                    return shift_to_domain(model)

            new_model = shift_to_model(shift)
            session.add(new_model)
            session.commit()
            shift.id = new_model.id
            return shift_to_domain(new_model)

    def get_by_id(self, shift_id: int) -> ShiftDefinition | None:
        with self.session_factory() as session:
            model = session.get(ShiftModel, shift_id)
            return shift_to_domain(model) if model else None

    def list_all(self) -> list[ShiftDefinition]:
        with self.session_factory() as session:
            stmt = select(ShiftModel).order_by(ShiftModel.id)
            models = session.scalars(stmt).all()
            return [shift_to_domain(m) for m in models]

    def delete(self, shift_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(ShiftModel, shift_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

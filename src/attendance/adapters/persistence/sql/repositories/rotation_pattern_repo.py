"""Adaptador SQLAlchemy para RotationPatternRepository."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    rotation_pattern_to_domain,
    rotation_pattern_to_model,
)
from attendance.adapters.persistence.sql.models import RotationPatternModel
from attendance.domain.schedule.rotation import RotationPattern
from attendance.ports.schedule.rotation_pattern_repository import RotationPatternRepository


class SqlRotationPatternRepository(RotationPatternRepository):
    """Implementación relacional del repositorio de patrones de rotación."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, pattern: RotationPattern) -> RotationPattern:
        with self.session_factory() as session:
            if pattern.id is not None:
                model = session.get(RotationPatternModel, pattern.id)
                if model:
                    model_data = rotation_pattern_to_model(pattern)
                    model.name = model_data.name
                    model.shift_sequence = model_data.shift_sequence
                    model.frequency = model_data.frequency
                    model.anchor_date = model_data.anchor_date
                    session.commit()
                    return rotation_pattern_to_domain(model)

            new_model = rotation_pattern_to_model(pattern)
            session.add(new_model)
            session.commit()
            pattern.id = new_model.id
            return rotation_pattern_to_domain(new_model)

    def get_by_id(self, pattern_id: int) -> RotationPattern | None:
        with self.session_factory() as session:
            model = session.get(RotationPatternModel, pattern_id)
            return rotation_pattern_to_domain(model) if model else None

    def list_all(self) -> list[RotationPattern]:
        with self.session_factory() as session:
            stmt = select(RotationPatternModel).order_by(RotationPatternModel.id)
            models = session.scalars(stmt).all()
            return [rotation_pattern_to_domain(m) for m in models]

    def delete(self, pattern_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(RotationPatternModel, pattern_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

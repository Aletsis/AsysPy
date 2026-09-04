from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    department_to_domain,
    position_to_domain,
    position_to_model,
)
from attendance.adapters.persistence.sql.models import (
    DepartmentModel,
    DepartmentPositionModel,
    PositionModel,
)
from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position
from attendance.ports.organization.position_repository import PositionRepository


class SqlPositionRepository(PositionRepository):
    """Implementación de PositionRepository respaldada por base de datos relacional."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, position: Position) -> Position:
        with self._session_factory() as session:
            model: PositionModel | None = None
            if position.id is not None:
                model = session.get(PositionModel, position.id)

            if model is None and position.code:
                model = session.scalar(
                    select(PositionModel).where(PositionModel.code == position.code)
                )

            if model is None:
                model = position_to_model(position)
                session.add(model)
                session.commit()
                session.refresh(model)
            else:
                model.name = position.name
                model.code = position.code
                model.description = position.description
                model.active = position.active
                session.commit()
                session.refresh(model)

            return position_to_domain(model)

    def save_all(self, positions: list[Position]) -> list[Position]:
        return [self.save(p) for p in positions]

    def get_by_id(self, position_id: int) -> Position | None:
        with self._session_factory() as session:
            model = session.get(PositionModel, position_id)
            if not model:
                return None
            return position_to_domain(model)

    def get_by_code(self, code: str) -> Position | None:
        cleaned = code.strip().upper()
        if not cleaned:
            return None
        with self._session_factory() as session:
            stmt = select(PositionModel).where(PositionModel.code == cleaned)
            model = session.scalar(stmt)
            if not model:
                return None
            return position_to_domain(model)

    def get_by_name(self, name: str) -> Position | None:
        cleaned = name.strip()
        if not cleaned:
            return None
        with self._session_factory() as session:
            stmt = select(PositionModel).where(func.lower(PositionModel.name) == cleaned.lower())
            model = session.scalar(stmt)
            if not model:
                return None
            return position_to_domain(model)

    def exists_by_id(self, position_id: int) -> bool:
        with self._session_factory() as session:
            stmt = select(PositionModel.id).where(PositionModel.id == position_id).limit(1)
            return session.scalar(stmt) is not None

    def exists_by_code(self, code: str) -> bool:
        cleaned = code.strip().upper()
        if not cleaned:
            return False
        with self._session_factory() as session:
            stmt = select(PositionModel.id).where(PositionModel.code == cleaned).limit(1)
            return session.scalar(stmt) is not None

    def list_all(
        self, department_id: int | None = None, active_only: bool = False
    ) -> list[Position]:
        with self._session_factory() as session:
            if department_id is not None:
                stmt = (
                    select(PositionModel)
                    .join(
                        DepartmentPositionModel,
                        PositionModel.id == DepartmentPositionModel.position_id,
                    )
                    .where(DepartmentPositionModel.department_id == department_id)
                )
            else:
                stmt = select(PositionModel)

            if active_only:
                stmt = stmt.where(PositionModel.active.is_(True))
            stmt = stmt.order_by(PositionModel.name.asc(), PositionModel.id.asc())
            models: Sequence[PositionModel] = session.scalars(stmt).all()
            return [position_to_domain(m) for m in models]

    def count(
        self, department_id: int | None = None, active_only: bool = False
    ) -> int:
        with self._session_factory() as session:
            if department_id is not None:
                stmt = (
                    select(func.count(PositionModel.id))
                    .join(
                        DepartmentPositionModel,
                        PositionModel.id == DepartmentPositionModel.position_id,
                    )
                    .where(DepartmentPositionModel.department_id == department_id)
                )
            else:
                stmt = select(func.count(PositionModel.id))

            if active_only:
                stmt = stmt.where(PositionModel.active.is_(True))
            total = session.scalar(stmt)
            return total if total is not None else 0

    def delete(self, position_id: int) -> bool:
        with self._session_factory() as session:
            model = session.get(PositionModel, position_id)
            if not model:
                return False
            # Limpiar asociaciones N:M
            session.execute(
                delete(DepartmentPositionModel).where(
                    DepartmentPositionModel.position_id == position_id
                )
            )
            session.delete(model)
            session.commit()
            return True

    def get_departments(
        self, position_id: int, active_only: bool = False
    ) -> list[Department]:
        with self._session_factory() as session:
            stmt = (
                select(DepartmentModel)
                .join(
                    DepartmentPositionModel,
                    DepartmentModel.id == DepartmentPositionModel.department_id,
                )
                .where(DepartmentPositionModel.position_id == position_id)
            )
            if active_only:
                stmt = stmt.where(DepartmentModel.active.is_(True))
            stmt = stmt.order_by(DepartmentModel.id)
            models = session.scalars(stmt).all()
            return [department_to_domain(m) for m in models]

    def assign_department(self, position_id: int, department_id: int) -> None:
        with self._session_factory() as session:
            existing = session.scalar(
                select(DepartmentPositionModel).where(
                    DepartmentPositionModel.position_id == position_id,
                    DepartmentPositionModel.department_id == department_id,
                )
            )
            if not existing:
                session.add(
                    DepartmentPositionModel(
                        position_id=position_id, department_id=department_id
                    )
                )
                session.commit()

    def remove_department(self, position_id: int, department_id: int) -> bool:
        with self._session_factory() as session:
            result = session.execute(
                delete(DepartmentPositionModel).where(
                    DepartmentPositionModel.position_id == position_id,
                    DepartmentPositionModel.department_id == department_id,
                )
            )
            session.commit()
            return bool(getattr(result, "rowcount", 0) > 0)

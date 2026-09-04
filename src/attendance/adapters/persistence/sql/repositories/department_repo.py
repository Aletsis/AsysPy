"""Repositorio SQL para Department usando SQLAlchemy."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    department_to_domain,
    department_to_model,
    position_to_domain,
)
from attendance.adapters.persistence.sql.models import (
    DepartmentModel,
    DepartmentPositionModel,
    PositionModel,
)
from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position
from attendance.ports.organization.department_repository import DepartmentRepository


class SqlDepartmentRepository(DepartmentRepository):
    """Implementación de DepartmentRepository respaldada por base de datos relacional."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, department: Department) -> Department:
        with self._session_factory() as session:
            model: DepartmentModel | None = None
            if department.id is not None:
                model = session.get(DepartmentModel, department.id)

            if model is None and department.code:
                model = session.scalar(
                    select(DepartmentModel).where(DepartmentModel.code == department.code)
                )

            if model is None:
                model = department_to_model(department)
                session.add(model)
                session.commit()
                session.refresh(model)
            else:
                model.name = department.name
                if department.code is not None:
                    model.code = department.code
                model.branch_id = department.branch_id
                model.active = department.active
                session.commit()
                session.refresh(model)

            return department_to_domain(model)

    def get_by_id(self, department_id: int) -> Department | None:
        with self._session_factory() as session:
            model = session.get(DepartmentModel, department_id)
            if not model:
                return None
            return department_to_domain(model)

    def get_by_code(self, code: str) -> Department | None:
        with self._session_factory() as session:
            stmt = select(DepartmentModel).where(DepartmentModel.code == code)
            model = session.scalar(stmt)
            if not model:
                return None
            return department_to_domain(model)

    def list_all(
        self, branch_id: int | None = None, active_only: bool = False
    ) -> list[Department]:
        with self._session_factory() as session:
            stmt = select(DepartmentModel)
            if branch_id is not None:
                stmt = stmt.where(DepartmentModel.branch_id == branch_id)
            if active_only:
                stmt = stmt.where(DepartmentModel.active.is_(True))
            stmt = stmt.order_by(DepartmentModel.id)
            models = session.scalars(stmt).all()
            return [department_to_domain(m) for m in models]

    def delete(self, department_id: int) -> bool:
        with self._session_factory() as session:
            model = session.get(DepartmentModel, department_id)
            if not model:
                return False
            # Limpiar asociaciones N:M con puestos
            session.execute(
                delete(DepartmentPositionModel).where(
                    DepartmentPositionModel.department_id == department_id
                )
            )
            session.delete(model)
            session.commit()
            return True

    def assign_position(self, department_id: int, position_id: int) -> None:
        """Asocia un puesto a un departamento si aún no está vinculado."""
        with self._session_factory() as session:
            existing = session.scalar(
                select(DepartmentPositionModel).where(
                    DepartmentPositionModel.department_id == department_id,
                    DepartmentPositionModel.position_id == position_id,
                )
            )
            if existing is None:
                assoc = DepartmentPositionModel(
                    department_id=department_id, position_id=position_id
                )
                session.add(assoc)
                session.commit()

    def remove_position(self, department_id: int, position_id: int) -> bool:
        """Desvincula un puesto de un departamento. Retorna True si existía."""
        with self._session_factory() as session:
            result = session.execute(
                delete(DepartmentPositionModel).where(
                    DepartmentPositionModel.department_id == department_id,
                    DepartmentPositionModel.position_id == position_id,
                )
            )
            session.commit()
            return result.rowcount > 0

    def get_positions(
        self, department_id: int, active_only: bool = False
    ) -> list[Position]:
        """Obtiene la lista de puestos asignados a un departamento."""
        with self._session_factory() as session:
            stmt = (
                select(PositionModel)
                .join(
                    DepartmentPositionModel,
                    PositionModel.id == DepartmentPositionModel.position_id,
                )
                .where(DepartmentPositionModel.department_id == department_id)
            )
            if active_only:
                stmt = stmt.where(PositionModel.active.is_(True))
            stmt = stmt.order_by(PositionModel.id)
            models = session.scalars(stmt).all()
            return [position_to_domain(m) for m in models]

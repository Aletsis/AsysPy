"""Repositorio SQL para Department usando SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    department_to_domain,
    department_to_model,
)
from attendance.adapters.persistence.sql.models import DepartmentModel
from attendance.domain.organization.department import Department
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
            session.delete(model)
            session.commit()
            return True

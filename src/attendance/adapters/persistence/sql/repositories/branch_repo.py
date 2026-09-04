"""Adaptador SQLAlchemy para BranchRepository (Sucursales)."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    address_to_dict,
    branch_to_domain,
    branch_to_model,
)
from attendance.adapters.persistence.sql.models import BranchModel
from attendance.domain.organization.branch import Branch
from attendance.ports.organization.branch_repository import BranchRepository


class SqlBranchRepository(BranchRepository):
    """Implementación relacional del repositorio de sucursales."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, branch: Branch) -> Branch:
        with self.session_factory() as session:
            existing: BranchModel | None = None
            if branch.id is not None:
                existing = session.get(BranchModel, branch.id)
            if existing is None and branch.code:
                stmt = select(BranchModel).where(BranchModel.code == branch.code)
                existing = session.scalars(stmt).first()

            if existing is not None:
                existing.name = branch.name
                existing.code = branch.code
                existing.timezone = branch.timezone
                existing.address = address_to_dict(branch.address)
                existing.email = branch.email
                existing.phone_number = branch.phone_number
                existing.active = branch.active
                session.commit()
                branch.id = existing.id
                return branch_to_domain(existing)
            else:
                model = branch_to_model(branch)
                session.add(model)
                session.commit()
                branch.id = model.id
                return branch_to_domain(model)

    def get_by_id(self, branch_id: int) -> Branch | None:
        with self.session_factory() as session:
            model = session.get(BranchModel, branch_id)
            return branch_to_domain(model) if model else None

    def get_by_code(self, code: str) -> Branch | None:
        with self.session_factory() as session:
            stmt = select(BranchModel).where(BranchModel.code == code)
            model = session.scalars(stmt).first()
            return branch_to_domain(model) if model else None

    def list_all(self, active_only: bool = False) -> list[Branch]:
        with self.session_factory() as session:
            stmt = select(BranchModel)
            if active_only:
                stmt = stmt.where(BranchModel.active.is_(True))
            stmt = stmt.order_by(BranchModel.id.asc())
            models = session.scalars(stmt).all()
            return [branch_to_domain(m) for m in models]

    def delete(self, branch_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(BranchModel, branch_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

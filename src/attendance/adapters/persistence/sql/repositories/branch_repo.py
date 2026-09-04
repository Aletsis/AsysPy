"""Adaptador SQLAlchemy para BranchRepository (Sucursales)."""

from sqlalchemy import func, select
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
                cleaned_code = branch.code.strip().upper()
                stmt = select(BranchModel).where(func.upper(BranchModel.code) == cleaned_code)
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

    def save_all(self, branches: list[Branch]) -> list[Branch]:
        return [self.save(b) for b in branches]

    def get_by_id(self, branch_id: int) -> Branch | None:
        with self.session_factory() as session:
            model = session.get(BranchModel, branch_id)
            return branch_to_domain(model) if model else None

    def get_by_code(self, code: str) -> Branch | None:
        cleaned = code.strip().upper()
        with self.session_factory() as session:
            stmt = select(BranchModel).where(func.upper(BranchModel.code) == cleaned)
            model = session.scalars(stmt).first()
            return branch_to_domain(model) if model else None

    def get_by_name(self, name: str) -> Branch | None:
        cleaned = name.strip().lower()
        with self.session_factory() as session:
            stmt = select(BranchModel).where(func.lower(BranchModel.name) == cleaned)
            model = session.scalars(stmt).first()
            return branch_to_domain(model) if model else None

    def exists_by_id(self, branch_id: int) -> bool:
        with self.session_factory() as session:
            stmt = select(func.count(BranchModel.id)).where(BranchModel.id == branch_id)
            count = session.scalar(stmt) or 0
            return count > 0

    def exists_by_code(self, code: str) -> bool:
        cleaned = code.strip().upper()
        with self.session_factory() as session:
            stmt = select(func.count(BranchModel.id)).where(func.upper(BranchModel.code) == cleaned)
            count = session.scalar(stmt) or 0
            return count > 0

    def list_all(self, active_only: bool = False) -> list[Branch]:
        with self.session_factory() as session:
            stmt = select(BranchModel)
            if active_only:
                stmt = stmt.where(BranchModel.active.is_(True))
            stmt = stmt.order_by(func.lower(BranchModel.name).asc(), BranchModel.id.asc())
            models = session.scalars(stmt).all()
            return [branch_to_domain(m) for m in models]

    def count(self, active_only: bool = False) -> int:
        with self.session_factory() as session:
            stmt = select(func.count(BranchModel.id))
            if active_only:
                stmt = stmt.where(BranchModel.active.is_(True))
            return session.scalar(stmt) or 0

    def delete(self, branch_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(BranchModel, branch_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False


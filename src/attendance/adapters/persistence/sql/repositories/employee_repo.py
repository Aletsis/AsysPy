from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    employee_to_domain,
    employee_to_model,
    fingerprint_to_model,
)
from attendance.adapters.persistence.sql.models import EmployeeFingerprintModel, EmployeeModel
from attendance.domain.organization.employee import Employee
from attendance.ports.organization import EmployeeRepository


class SqlEmployeeRepository(EmployeeRepository):
    """Implementación relacional del repositorio de empleados."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def _load_fingerprints(self, session: Session, pin: str) -> list[EmployeeFingerprintModel]:
        stmt = select(EmployeeFingerprintModel).where(EmployeeFingerprintModel.employee_pin == pin)
        return list(session.scalars(stmt).all())

    def save(self, employee: Employee) -> Employee:
        with self.session_factory() as session:
            existing: EmployeeModel | None = None
            if employee.id is not None:
                existing = session.get(EmployeeModel, employee.id)
            if existing is None:
                stmt = select(EmployeeModel).where(EmployeeModel.pin == employee.pin)
                existing = session.scalars(stmt).first()

            if existing is not None:
                existing.pin = employee.pin
                existing.first_name = employee.first_name
                existing.paternal_last_name = employee.paternal_last_name
                existing.maternal_last_name = employee.maternal_last_name
                existing.hire_date = employee.hire_date
                existing.sex = employee.sex.value
                existing.department_id = employee.department_id
                existing.position_id = employee.position_id
                existing.position = employee.position
                existing.home_branch_id = employee.home_branch_id
                existing.active = employee.active
                existing.email = employee.email
                existing.phone_number = employee.phone_number
                existing.curp = employee.curp
                existing.rfc = employee.rfc
                existing.password = employee.password
                existing.card_number = employee.card_number
                model = existing
            else:
                model = employee_to_model(employee)
                session.add(model)

            # Sincronizar huellas asociadas
            del_stmt = delete(EmployeeFingerprintModel).where(EmployeeFingerprintModel.employee_pin == employee.pin)
            session.execute(del_stmt)
            for fp in employee.fingerprints:
                session.add(fingerprint_to_model(fp, employee.pin))

            session.commit()
            employee.id = model.id

            fps = self._load_fingerprints(session, employee.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def save_all(self, employees: list[Employee]) -> list[Employee]:
        return [self.save(emp) for emp in employees]

    def get_by_pin(self, pin: str) -> Employee | None:
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.pin == pin)
            model = session.scalars(stmt).first()
            if not model:
                return None
            fps = self._load_fingerprints(session, pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def get_by_id(self, employee_id: int) -> Employee | None:
        with self.session_factory() as session:
            model = session.get(EmployeeModel, employee_id)
            if not model:
                return None
            fps = self._load_fingerprints(session, model.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def get_by_curp(self, curp: str) -> Employee | None:
        cleaned = curp.strip().upper()
        if not cleaned:
            return None
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.curp == cleaned)
            model = session.scalars(stmt).first()
            if not model:
                return None
            fps = self._load_fingerprints(session, model.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def get_by_rfc(self, rfc: str) -> Employee | None:
        cleaned = rfc.strip().upper()
        if not cleaned:
            return None
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.rfc == cleaned)
            model = session.scalars(stmt).first()
            if not model:
                return None
            fps = self._load_fingerprints(session, model.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def get_by_card_number(self, card_number: str) -> Employee | None:
        cleaned = card_number.strip()
        if not cleaned:
            return None
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.card_number == cleaned)
            model = session.scalars(stmt).first()
            if not model:
                return None
            fps = self._load_fingerprints(session, model.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def get_by_email(self, email: str) -> Employee | None:
        cleaned = email.strip().lower()
        if not cleaned:
            return None
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.email == cleaned)
            model = session.scalars(stmt).first()
            if not model:
                return None
            fps = self._load_fingerprints(session, model.pin)
            return employee_to_domain(model, fingerprint_models=fps)

    def exists_by_pin(self, pin: str) -> bool:
        with self.session_factory() as session:
            stmt = select(EmployeeModel.id).where(EmployeeModel.pin == pin).limit(1)
            return session.scalar(stmt) is not None

    def exists_by_id(self, employee_id: int) -> bool:
        with self.session_factory() as session:
            stmt = select(EmployeeModel.id).where(EmployeeModel.id == employee_id).limit(1)
            return session.scalar(stmt) is not None

    def list_active(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_all(branch_id=branch_id, active_only=True)

    def get_active_employees(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_active(branch_id=branch_id)

    def list_all(
        self,
        branch_id: int | None = None,
        department_id: int | None = None,
        position_id: int | None = None,
        active_only: bool = False,
    ) -> list[Employee]:
        with self.session_factory() as session:
            stmt = select(EmployeeModel)
            if active_only:
                stmt = stmt.where(EmployeeModel.active.is_(True))
            if branch_id is not None:
                stmt = stmt.where(EmployeeModel.home_branch_id == branch_id)
            if department_id is not None:
                stmt = stmt.where(EmployeeModel.department_id == department_id)
            if position_id is not None:
                stmt = stmt.where(EmployeeModel.position_id == position_id)
            stmt = stmt.order_by(EmployeeModel.paternal_last_name.asc(), EmployeeModel.first_name.asc())
            models: Sequence[EmployeeModel] = session.scalars(stmt).all()
            return [employee_to_domain(m) for m in models]

    def count(
        self,
        branch_id: int | None = None,
        department_id: int | None = None,
        position_id: int | None = None,
        active_only: bool = False,
    ) -> int:
        with self.session_factory() as session:
            stmt = select(func.count(EmployeeModel.id))
            if active_only:
                stmt = stmt.where(EmployeeModel.active.is_(True))
            if branch_id is not None:
                stmt = stmt.where(EmployeeModel.home_branch_id == branch_id)
            if department_id is not None:
                stmt = stmt.where(EmployeeModel.department_id == department_id)
            if position_id is not None:
                stmt = stmt.where(EmployeeModel.position_id == position_id)
            total = session.scalar(stmt)
            return total if total is not None else 0

    def delete(self, pin: str) -> bool:
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.pin == pin)
            model = session.scalars(stmt).first()
            if model:
                del_fps = delete(EmployeeFingerprintModel).where(EmployeeFingerprintModel.employee_pin == pin)
                session.execute(del_fps)
                session.delete(model)
                session.commit()
                return True
            return False

    def delete_by_id(self, employee_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(EmployeeModel, employee_id)
            if model:
                del_fps = delete(EmployeeFingerprintModel).where(EmployeeFingerprintModel.employee_pin == model.pin)
                session.execute(del_fps)
                session.delete(model)
                session.commit()
                return True
            return False

"""Adaptador SQLAlchemy para EmployeeRepository."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    employee_to_domain,
    employee_to_model,
)
from attendance.adapters.persistence.sql.models import EmployeeModel
from attendance.domain.organization.employee import Employee
from attendance.ports.organization import EmployeeRepository


class SqlEmployeeRepository(EmployeeRepository):
    """Implementación relacional del repositorio de empleados."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

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
                existing.position = employee.position
                existing.home_branch_id = employee.home_branch_id
                existing.active = employee.active
                session.commit()
                employee.id = existing.id
                return employee_to_domain(existing)
            else:
                model = employee_to_model(employee)
                session.add(model)
                session.commit()
                employee.id = model.id
                return employee_to_domain(model)

    def get_by_pin(self, pin: str) -> Employee | None:
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.pin == pin)
            model = session.scalars(stmt).first()
            return employee_to_domain(model) if model else None

    def get_by_id(self, employee_id: int) -> Employee | None:
        with self.session_factory() as session:
            model = session.get(EmployeeModel, employee_id)
            return employee_to_domain(model) if model else None

    def list_active(self, branch_id: int | None = None) -> list[Employee]:
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.active.is_(True))
            if branch_id is not None:
                stmt = stmt.where(EmployeeModel.home_branch_id == branch_id)
            stmt = stmt.order_by(EmployeeModel.paternal_last_name.asc(), EmployeeModel.first_name.asc())
            models = session.scalars(stmt).all()
            return [employee_to_domain(m) for m in models]

    def get_active_employees(self, branch_id: int | None = None) -> list[Employee]:
        return self.list_active(branch_id=branch_id)

    def list_all(self, branch_id: int | None = None) -> list[Employee]:
        with self.session_factory() as session:
            stmt = select(EmployeeModel)
            if branch_id is not None:
                stmt = stmt.where(EmployeeModel.home_branch_id == branch_id)
            stmt = stmt.order_by(EmployeeModel.paternal_last_name.asc(), EmployeeModel.first_name.asc())
            models = session.scalars(stmt).all()
            return [employee_to_domain(m) for m in models]

    def delete(self, pin: str) -> bool:
        with self.session_factory() as session:
            stmt = select(EmployeeModel).where(EmployeeModel.pin == pin)
            model = session.scalars(stmt).first()
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

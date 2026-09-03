"""Adaptador SQLAlchemy para EmployeeScheduleAssignmentRepository."""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    schedule_assignment_to_domain,
    schedule_assignment_to_model,
)
from attendance.adapters.persistence.sql.models import ScheduleAssignmentModel
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.ports.schedule import EmployeeScheduleAssignmentRepository


class SqlScheduleAssignmentRepository(EmployeeScheduleAssignmentRepository):
    """Implementación relacional del repositorio de asignaciones de horarios."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def get_active_assignment(
        self, employee_pin: str, as_of: date
    ) -> EmployeeScheduleAssignment | None:
        with self.session_factory() as session:
            stmt = (
                select(ScheduleAssignmentModel)
                .where(
                    ScheduleAssignmentModel.employee_pin == employee_pin,
                    ScheduleAssignmentModel.valid_from <= as_of,
                    or_(
                        ScheduleAssignmentModel.valid_until.is_(None),
                        ScheduleAssignmentModel.valid_until >= as_of,
                    ),
                )
                .order_by(ScheduleAssignmentModel.valid_from.desc(), ScheduleAssignmentModel.id.desc())
            )
            model = session.scalars(stmt).first()
            return schedule_assignment_to_domain(model) if model else None

    def close_assignment(self, assignment_id: int, valid_until: date) -> None:
        with self.session_factory() as session:
            model = session.get(ScheduleAssignmentModel, assignment_id)
            if model:
                model.valid_until = valid_until
                session.commit()

    def save(
        self, assignment: EmployeeScheduleAssignment
    ) -> EmployeeScheduleAssignment:
        with self.session_factory() as session:
            if assignment.id is not None:
                model = session.get(ScheduleAssignmentModel, assignment.id)
                if model:
                    model.employee_pin = assignment.employee_pin
                    model.mode = assignment.mode.value
                    model.valid_from = assignment.valid_from
                    model.valid_until = assignment.valid_until
                    model.working_weekdays = (
                        [w.value for w in assignment.working_weekdays]
                        if assignment.working_weekdays is not None
                        else None
                    )
                    model.shift_definition_id = assignment.shift_definition_id
                    model.rotation_pattern_id = assignment.rotation_pattern_id
                    model.expected_min_sessions = assignment.expected_min_sessions
                    session.commit()
                    return schedule_assignment_to_domain(model)

            new_model = schedule_assignment_to_model(assignment)
            session.add(new_model)
            session.commit()
            assignment.id = new_model.id
            return schedule_assignment_to_domain(new_model)

    def get_by_id(self, assignment_id: int) -> EmployeeScheduleAssignment | None:
        with self.session_factory() as session:
            model = session.get(ScheduleAssignmentModel, assignment_id)
            return schedule_assignment_to_domain(model) if model else None

    def list_all(
        self, employee_pin: str | None = None
    ) -> list[EmployeeScheduleAssignment]:
        with self.session_factory() as session:
            stmt = select(ScheduleAssignmentModel)
            if employee_pin:
                stmt = stmt.where(ScheduleAssignmentModel.employee_pin == employee_pin)
            stmt = stmt.order_by(ScheduleAssignmentModel.valid_from.desc(), ScheduleAssignmentModel.id.desc())
            models = session.scalars(stmt).all()
            return [schedule_assignment_to_domain(m) for m in models]

    def delete(self, assignment_id: int) -> bool:
        with self.session_factory() as session:
            model = session.get(ScheduleAssignmentModel, assignment_id)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

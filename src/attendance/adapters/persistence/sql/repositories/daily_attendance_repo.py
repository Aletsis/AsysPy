"""Adaptador SQLAlchemy para DailyAttendanceRepository (Jornadas evaluadas)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    daily_attendance_to_domain,
    shift_to_dict,
    work_session_to_model,
)
from attendance.adapters.persistence.sql.models import (
    DailyAttendanceModel,
    EmployeeModel,
)
from attendance.domain.attendance.daily_attendance import DailyAttendance
from attendance.ports.attendance import DailyAttendanceRepository


class SqlDailyAttendanceRepository(DailyAttendanceRepository):
    """Implementación relacional del repositorio de jornadas diarias procesadas."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, daily_attendance: DailyAttendance) -> DailyAttendance:
        with self.session_factory() as session:
            stmt = (
                select(DailyAttendanceModel)
                .options(selectinload(DailyAttendanceModel.sessions))
                .where(
                    DailyAttendanceModel.employee_pin == daily_attendance.employee_pin,
                    DailyAttendanceModel.date == daily_attendance.date,
                )
            )
            existing = session.scalars(stmt).first()

            if existing is not None:
                # Actualizar campos existentes
                existing.status = daily_attendance.status.value
                existing.first_check_in = daily_attendance.first_check_in
                existing.last_check_out = daily_attendance.last_check_out
                existing.tardiness_minutes = daily_attendance.tardiness_minutes
                existing.early_departure_minutes = daily_attendance.early_departure_minutes
                existing.total_worked_minutes = daily_attendance.total_worked_minutes
                existing.total_break_minutes = daily_attendance.total_break_minutes
                existing.overtime_minutes = daily_attendance.overtime_minutes
                existing.notes = daily_attendance.notes
                existing.expected_shift_id = (
                    daily_attendance.expected_shift.id if daily_attendance.expected_shift else None
                )
                existing.expected_shift_data = shift_to_dict(daily_attendance.expected_shift)

                # Reemplazar sesiones (orphan removal las borrará en la BD)
                existing.sessions.clear()
                for s in daily_attendance.sessions:
                    ws_model = work_session_to_model(s, daily_attendance_id=existing.id)
                    existing.sessions.append(ws_model)

                session.commit()
                return daily_attendance_to_domain(existing)
            else:
                new_model = DailyAttendanceModel(
                    employee_pin=daily_attendance.employee_pin,
                    date=daily_attendance.date,
                    status=daily_attendance.status.value,
                    first_check_in=daily_attendance.first_check_in,
                    last_check_out=daily_attendance.last_check_out,
                    tardiness_minutes=daily_attendance.tardiness_minutes,
                    early_departure_minutes=daily_attendance.early_departure_minutes,
                    total_worked_minutes=daily_attendance.total_worked_minutes,
                    total_break_minutes=daily_attendance.total_break_minutes,
                    overtime_minutes=daily_attendance.overtime_minutes,
                    notes=daily_attendance.notes,
                    expected_shift_id=(
                        daily_attendance.expected_shift.id
                        if daily_attendance.expected_shift
                        else None
                    ),
                    expected_shift_data=shift_to_dict(daily_attendance.expected_shift),
                )
                session.add(new_model)
                session.flush()

                for s in daily_attendance.sessions:
                    ws_model = work_session_to_model(s, daily_attendance_id=new_model.id)
                    new_model.sessions.append(ws_model)

                session.commit()
                return daily_attendance_to_domain(new_model)

    def get_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> DailyAttendance | None:
        with self.session_factory() as session:
            stmt = (
                select(DailyAttendanceModel)
                .options(selectinload(DailyAttendanceModel.sessions))
                .where(
                    DailyAttendanceModel.employee_pin == employee_pin,
                    DailyAttendanceModel.date == target_date,
                )
            )
            model = session.scalars(stmt).first()
            return daily_attendance_to_domain(model) if model else None

    def get_by_employee_and_date_range(
        self, employee_pin: str, start_date: date, end_date: date
    ) -> list[DailyAttendance]:
        with self.session_factory() as session:
            stmt = (
                select(DailyAttendanceModel)
                .options(selectinload(DailyAttendanceModel.sessions))
                .where(
                    DailyAttendanceModel.employee_pin == employee_pin,
                    DailyAttendanceModel.date >= start_date,
                    DailyAttendanceModel.date <= end_date,
                )
                .order_by(DailyAttendanceModel.date.asc())
            )
            models = session.scalars(stmt).all()
            return [daily_attendance_to_domain(m) for m in models]

    def get_by_date_range(
        self, employee_pin: str, from_date: date, to_date: date
    ) -> list[DailyAttendance]:
        return self.get_by_employee_and_date_range(employee_pin, from_date, to_date)

    def list_by_date(
        self, target_date: date, branch_id: int | None = None
    ) -> list[DailyAttendance]:
        with self.session_factory() as session:
            stmt = (
                select(DailyAttendanceModel)
                .options(selectinload(DailyAttendanceModel.sessions))
                .where(DailyAttendanceModel.date == target_date)
            )
            if branch_id is not None:
                stmt = stmt.join(
                    EmployeeModel,
                    EmployeeModel.pin == DailyAttendanceModel.employee_pin,
                ).where(EmployeeModel.home_branch_id == branch_id)

            stmt = stmt.order_by(DailyAttendanceModel.employee_pin.asc())
            models = session.scalars(stmt).all()
            return [daily_attendance_to_domain(m) for m in models]

"""Adaptador SQLAlchemy para AttendanceRepository (Marcaciones crudas)."""

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.mappers import (
    attendance_log_to_domain,
    attendance_log_to_model,
)
from attendance.adapters.persistence.sql.models import AttendanceLogModel
from attendance.domain.device.enums import LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.ports.attendance import AttendanceRepository


class SqlAttendanceRepository(AttendanceRepository):
    """Implementación relacional del repositorio de marcaciones crudas."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save_raw_log(self, log: AttendanceLog) -> None:
        with self.session_factory() as session:
            model = attendance_log_to_model(log)
            session.add(model)
            session.commit()
            log.id = model.id

    def get_unprocessed_logs(self) -> list[AttendanceLog]:
        with self.session_factory() as session:
            stmt = (
                select(AttendanceLogModel)
                .where(AttendanceLogModel.processing_status == LogStatus.RAW.value)
                .order_by(AttendanceLogModel.timestamp.asc())
            )
            models = session.scalars(stmt).all()
            return [attendance_log_to_domain(m) for m in models]

    def mark_as_processed(self, log_id: int, inferred_type: str) -> None:
        with self.session_factory() as session:
            model = session.get(AttendanceLogModel, log_id)
            if model:
                model.processing_status = LogStatus.PROCESSED.value
                model.inferred_type = inferred_type
                session.commit()

    def get_by_id(self, log_id: int) -> AttendanceLog | None:
        with self.session_factory() as session:
            model = session.get(AttendanceLogModel, log_id)
            return attendance_log_to_domain(model) if model else None

    def get_logs_by_employee_and_date(
        self, employee_pin: str, target_date: date
    ) -> list[AttendanceLog]:
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        with self.session_factory() as session:
            stmt = (
                select(AttendanceLogModel)
                .where(
                    AttendanceLogModel.employee_pin == employee_pin,
                    AttendanceLogModel.timestamp >= start_dt,
                    AttendanceLogModel.timestamp <= end_dt,
                    AttendanceLogModel.processing_status != LogStatus.IGNORED.value,
                )
                .order_by(AttendanceLogModel.timestamp.asc())
            )
            models = session.scalars(stmt).all()
            return [attendance_log_to_domain(m) for m in models]

    def get_logs_for_employee(
        self, employee_pin: str, start_time: datetime, end_time: datetime
    ) -> list[AttendanceLog]:
        with self.session_factory() as session:
            stmt = (
                select(AttendanceLogModel)
                .where(
                    AttendanceLogModel.employee_pin == employee_pin,
                    AttendanceLogModel.timestamp >= start_time,
                    AttendanceLogModel.timestamp <= end_time,
                    AttendanceLogModel.processing_status != LogStatus.IGNORED.value,
                )
                .order_by(AttendanceLogModel.timestamp.asc())
            )
            models = session.scalars(stmt).all()
            return [attendance_log_to_domain(m) for m in models]

    def update_log(self, log: AttendanceLog) -> AttendanceLog:
        with self.session_factory() as session:
            if log.id is None:
                new_model = attendance_log_to_model(log)
                session.add(new_model)
                session.commit()
                log.id = new_model.id
            else:
                existing_model = session.get(AttendanceLogModel, log.id)
                if existing_model is not None:
                    existing_model.record_uid = log.record_uid
                    existing_model.employee_pin = log.employee_pin
                    existing_model.device_id = log.device_id
                    existing_model.timestamp = log.timestamp
                    existing_model.raw_status = log.raw_status
                    existing_model.raw_punch = log.raw_punch
                    existing_model.auth_method = log.auth_method.value
                    existing_model.processing_status = log.processing_status.value
                    existing_model.inferred_type = log.inferred_type
                    session.commit()
                else:
                    new_model = attendance_log_to_model(log)
                    session.add(new_model)
                    session.commit()
            return log

    def list_all(self) -> list[AttendanceLog]:
        with self.session_factory() as session:
            stmt = select(AttendanceLogModel).order_by(AttendanceLogModel.timestamp.asc())
            models = session.scalars(stmt).all()
            return [attendance_log_to_domain(m) for m in models]

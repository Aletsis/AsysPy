"""Modelos de datos SQLAlchemy 2.0 para persistencia relacional agnóstica.

Soporta SQLite, PostgreSQL, MySQL y Microsoft SQL Server sin acoplar
ninguna regla de negocio del dominio.
"""

from datetime import date, datetime, time
from typing import Any, List

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base declarativa para todas las entidades relacionales de AsistPy."""
    pass


class AttendanceLogModel(Base):
    """Tabla de marcaciones crudas provenientes de dispositivos biométricos."""

    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_uid: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    raw_status: Mapped[int] = mapped_column(Integer, default=0)
    raw_punch: Mapped[int] = mapped_column(Integer, default=1)
    auth_method: Mapped[str] = mapped_column(String(30), default="fingerprint")
    processing_status: Mapped[str] = mapped_column(String(30), default="raw", index=True)
    inferred_type: Mapped[str | None] = mapped_column(String(50), nullable=True)


class EmployeeModel(Base):
    """Tabla de empleados y personal de la organización."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pin: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    paternal_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    maternal_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    home_branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    curp: Mapped[str | None] = mapped_column(String(18), nullable=True, index=True)
    rfc: Mapped[str | None] = mapped_column(String(13), nullable=True, index=True)
    password: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)


class EmployeeFingerprintModel(Base):
    """Tabla para almacenar plantillas biométricas de huellas dactilares."""

    __tablename__ = "employee_fingerprints"
    __table_args__ = (
        UniqueConstraint("employee_pin", "finger_index", name="uq_employee_fingerprint_pin_finger"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    finger_index: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), default="10.0", nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)


class DailyAttendanceModel(Base):
    """Tabla de jornadas diarias de asistencia evaluadas y consolidadas."""

    __tablename__ = "daily_attendances"
    __table_args__ = (
        UniqueConstraint("employee_pin", "date", name="uq_daily_attendance_employee_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    first_check_in: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_out: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tardiness_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_departure_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_shift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_shift_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    sessions: Mapped[List["WorkSessionModel"]] = relationship(
        "WorkSessionModel",
        back_populates="daily_attendance",
        cascade="all, delete-orphan",
        order_by="WorkSessionModel.check_in",
    )


class WorkSessionModel(Base):
    """Tabla de sesiones de trabajo (pares o bloques de entrada/salida)."""

    __tablename__ = "work_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_attendance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("daily_attendances.id", ondelete="CASCADE"), nullable=True, index=True
    )
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    check_out: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_out_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_in_device_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_out_device_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    daily_attendance: Mapped[DailyAttendanceModel | None] = relationship(
        "DailyAttendanceModel", back_populates="sessions"
    )


class JustificationModel(Base):
    """Tabla de justificaciones, vacaciones e incidencias laborales."""

    __tablename__ = "justifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="approved", nullable=False)
    support_document: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)


class AuditLogModel(Base):
    """Tabla inmutable de trazabilidad de auditoría de ajustes y operaciones."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
    previous_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    employee_pin: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)


class ScheduleAssignmentModel(Base):
    """Tabla de asignaciones de horarios y turnos a empleados."""

    __tablename__ = "schedule_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_pin: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    working_weekdays: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    shift_definition_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotation_pattern_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_min_sessions: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SyncStateModel(Base):
    """Tabla de control de marcas de agua para sincronización de dispositivos biométricos."""

    __tablename__ = "sync_states"

    device_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_synced_uid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DeviceModel(Base):
    """Tabla del catálogo de relojes checadores / dispositivos biométricos."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(30), default="tcp_4370", nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, default=4370, nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ShiftModel(Base):
    """Tabla de catálogo de turnos laborales (regulares, nocturnos, partidos, etc.)."""

    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="personalizado", nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    tolerance_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    segments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)


class RotationPatternModel(Base):
    """Tabla de patrones de rotación cíclica de turnos (6x1, 24x48, etc.)."""

    __tablename__ = "rotation_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift_sequence: Mapped[list[int | None]] = mapped_column(JSON, nullable=False)
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    anchor_date: Mapped[date] = mapped_column(Date, nullable=False)


class BranchModel(Base):
    """Tabla del catálogo de sucursales u oficinas físicas."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Mexico_City", nullable=False)
    address: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class DepartmentModel(Base):
    """Tabla del catálogo de departamentos u áreas operativas."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)





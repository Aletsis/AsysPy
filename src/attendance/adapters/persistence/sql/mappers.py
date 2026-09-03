"""Mapeadores bidireccionales entre modelos SQLAlchemy y entidades de dominio puras.

Garantiza que el Dominio permanezca completamente desacoplado de la base de datos.
"""

from datetime import time
from typing import Any

from attendance.adapters.persistence.sql.models import (
    AttendanceLogModel,
    AuditLogModel,
    DailyAttendanceModel,
    EmployeeModel,
    JustificationModel,
    ScheduleAssignmentModel,
    WorkSessionModel,
)
from attendance.domain.attendance.daily_attendance import DailyAttendance
from attendance.domain.attendance.enums import AttendanceStatus, SessionStatus, SessionType
from attendance.domain.attendance.session import WorkSession
from attendance.domain.audit.audit_log import AuditAction, AuditLog
from attendance.domain.device.enums import AuthMethod, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.incidence.enums import JustificationStatus, JustificationType
from attendance.domain.incidence.justification import Justification
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, ShiftCategory, Weekday
from attendance.domain.schedule.shift import ShiftDefinition, ShiftSegment


# ============================================================================
# AttendanceLog Mappers
# ============================================================================
def attendance_log_to_domain(model: AttendanceLogModel) -> AttendanceLog:
    """Convierte un AttendanceLogModel a la entidad AttendanceLog del dominio."""
    return AttendanceLog(
        id=model.id,
        record_uid=model.record_uid,
        employee_pin=model.employee_pin,
        device_id=model.device_id,
        timestamp=model.timestamp,
        raw_status=model.raw_status,
        raw_punch=model.raw_punch,
        auth_method=AuthMethod(model.auth_method),
        processing_status=LogStatus(model.processing_status),
        inferred_type=model.inferred_type,
    )


def attendance_log_to_model(entity: AttendanceLog) -> AttendanceLogModel:
    """Convierte una entidad AttendanceLog a AttendanceLogModel."""
    return AttendanceLogModel(
        id=entity.id if entity.id is not None else None,
        record_uid=entity.record_uid,
        employee_pin=entity.employee_pin,
        device_id=entity.device_id,
        timestamp=entity.timestamp,
        raw_status=entity.raw_status,
        raw_punch=entity.raw_punch,
        auth_method=entity.auth_method.value,
        processing_status=entity.processing_status.value,
        inferred_type=entity.inferred_type,
    )


# ============================================================================
# Employee Mappers
# ============================================================================
def employee_to_domain(model: EmployeeModel) -> Employee:
    """Convierte un EmployeeModel a la entidad Employee del dominio."""
    return Employee(
        id=model.id,
        pin=model.pin,
        first_name=model.first_name,
        paternal_last_name=model.paternal_last_name,
        maternal_last_name=model.maternal_last_name,
        hire_date=model.hire_date,
        sex=Sex(model.sex),
        department_id=model.department_id,
        position=model.position,
        home_branch_id=model.home_branch_id,
        active=model.active,
    )


def employee_to_model(entity: Employee) -> EmployeeModel:
    """Convierte una entidad Employee a EmployeeModel."""
    return EmployeeModel(
        id=entity.id if entity.id is not None else None,
        pin=entity.pin,
        first_name=entity.first_name,
        paternal_last_name=entity.paternal_last_name,
        maternal_last_name=entity.maternal_last_name,
        hire_date=entity.hire_date,
        sex=entity.sex.value,
        department_id=entity.department_id,
        position=entity.position,
        home_branch_id=entity.home_branch_id,
        active=entity.active,
    )


# ============================================================================
# WorkSession Mappers
# ============================================================================
def work_session_to_domain(model: WorkSessionModel) -> WorkSession:
    """Convierte un WorkSessionModel a la entidad WorkSession del dominio."""
    return WorkSession(
        id=model.id,
        employee_pin=model.employee_pin,
        check_in=model.check_in,
        check_out=model.check_out,
        check_in_log_id=model.check_in_log_id,
        check_out_log_id=model.check_out_log_id,
        check_in_device_id=model.check_in_device_id,
        check_out_device_id=model.check_out_device_id,
        session_type=SessionType(model.session_type),
        status=SessionStatus(model.status),
    )


def work_session_to_model(
    entity: WorkSession, daily_attendance_id: int | None = None
) -> WorkSessionModel:
    """Convierte una entidad WorkSession a WorkSessionModel."""
    return WorkSessionModel(
        id=entity.id if entity.id is not None else None,
        daily_attendance_id=daily_attendance_id,
        employee_pin=entity.employee_pin,
        check_in=entity.check_in,
        check_out=entity.check_out,
        check_in_log_id=entity.check_in_log_id,
        check_out_log_id=entity.check_out_log_id,
        check_in_device_id=entity.check_in_device_id,
        check_out_device_id=entity.check_out_device_id,
        session_type=entity.session_type.value,
        status=entity.status.value,
    )


# ============================================================================
# ShiftDefinition Helpers (JSON Serialization)
# ============================================================================
def shift_to_dict(shift: ShiftDefinition | None) -> dict[str, Any] | None:
    """Serializa un ShiftDefinition a un diccionario JSON."""
    if shift is None:
        return None
    return {
        "id": shift.id,
        "name": shift.name,
        "category": shift.category.value,
        "start_time": shift.start_time.isoformat() if shift.start_time else None,
        "end_time": shift.end_time.isoformat() if shift.end_time else None,
        "tolerance_minutes": shift.tolerance_minutes,
        "crosses_midnight": shift.crosses_midnight,
        "segments": [
            {
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "crosses_midnight": s.crosses_midnight,
                "tolerance_minutes": s.tolerance_minutes,
                "name": s.name,
            }
            for s in shift.segments
        ],
    }


def shift_from_dict(data: dict[str, Any] | None) -> ShiftDefinition | None:
    """Deserializa un diccionario JSON a ShiftDefinition."""
    if not data:
        return None
    segments = [
        ShiftSegment(
            start_time=time.fromisoformat(s["start_time"]),
            end_time=time.fromisoformat(s["end_time"]),
            crosses_midnight=s.get("crosses_midnight", False),
            tolerance_minutes=s.get("tolerance_minutes", 0),
            name=s.get("name", "Segmento"),
        )
        for s in data.get("segments", [])
    ]
    return ShiftDefinition(
        id=data["id"],
        name=data["name"],
        category=ShiftCategory(data.get("category", ShiftCategory.PERSONALIZADO.value)),
        start_time=time.fromisoformat(data["start_time"]) if data.get("start_time") else None,
        end_time=time.fromisoformat(data["end_time"]) if data.get("end_time") else None,
        tolerance_minutes=data.get("tolerance_minutes", 0),
        crosses_midnight=data.get("crosses_midnight", False),
        segments=segments,
    )


# ============================================================================
# DailyAttendance Mappers
# ============================================================================
def daily_attendance_to_domain(model: DailyAttendanceModel) -> DailyAttendance:
    """Convierte un DailyAttendanceModel a la entidad DailyAttendance del dominio."""
    sessions = [work_session_to_domain(s) for s in model.sessions]
    expected_shift = shift_from_dict(model.expected_shift_data)
    daily = DailyAttendance(
        employee_pin=model.employee_pin,
        date=model.date,
        expected_shift=expected_shift,
        sessions=sessions,
        status=AttendanceStatus(model.status),
        first_check_in=model.first_check_in,
        last_check_out=model.last_check_out,
        tardiness_minutes=model.tardiness_minutes,
        early_departure_minutes=model.early_departure_minutes,
        total_worked_minutes=model.total_worked_minutes,
        total_break_minutes=model.total_break_minutes,
        overtime_minutes=model.overtime_minutes,
        notes=model.notes,
    )
    return daily


def daily_attendance_to_model(entity: DailyAttendance) -> DailyAttendanceModel:
    """Convierte una entidad DailyAttendance a DailyAttendanceModel con sus sesiones."""
    model = DailyAttendanceModel(
        employee_pin=entity.employee_pin,
        date=entity.date,
        status=entity.status.value,
        first_check_in=entity.first_check_in,
        last_check_out=entity.last_check_out,
        tardiness_minutes=entity.tardiness_minutes,
        early_departure_minutes=entity.early_departure_minutes,
        total_worked_minutes=entity.total_worked_minutes,
        total_break_minutes=entity.total_break_minutes,
        overtime_minutes=entity.overtime_minutes,
        notes=entity.notes,
        expected_shift_id=entity.expected_shift.id if entity.expected_shift else None,
        expected_shift_data=shift_to_dict(entity.expected_shift),
    )
    model.sessions = [work_session_to_model(s) for s in entity.sessions]
    return model


# ============================================================================
# Justification Mappers
# ============================================================================
def justification_to_domain(model: JustificationModel) -> Justification:
    """Convierte un JustificationModel a la entidad Justification del dominio."""
    return Justification(
        id=model.id,
        employee_pin=model.employee_pin,
        type=JustificationType(model.type),
        start_date=model.start_date,
        end_date=model.end_date,
        reason=model.reason,
        approved_by=model.approved_by,
        status=JustificationStatus(model.status),
        support_document=model.support_document,
        created_at=model.created_at,
        start_time=model.start_time,
        end_time=model.end_time,
    )


def justification_to_model(entity: Justification) -> JustificationModel:
    """Convierte una entidad Justification a JustificationModel."""
    return JustificationModel(
        id=entity.id if entity.id is not None else None,
        employee_pin=entity.employee_pin,
        type=entity.type.value,
        start_date=entity.start_date,
        end_date=entity.end_date,
        reason=entity.reason,
        approved_by=entity.approved_by,
        status=entity.status.value,
        support_document=entity.support_document,
        created_at=entity.created_at,
        start_time=entity.start_time,
        end_time=entity.end_time,
    )


# ============================================================================
# AuditLog Mappers
# ============================================================================
def audit_log_to_domain(model: AuditLogModel) -> AuditLog:
    """Convierte un AuditLogModel a la entidad AuditLog del dominio."""
    return AuditLog(
        id=model.id,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        action=AuditAction(model.action),
        performed_by=model.performed_by,
        reason=model.reason,
        timestamp=model.timestamp,
        previous_value=model.previous_value,
        new_value=model.new_value,
        employee_pin=model.employee_pin,
    )


def audit_log_to_model(entity: AuditLog) -> AuditLogModel:
    """Convierte una entidad AuditLog a AuditLogModel."""
    return AuditLogModel(
        id=entity.id if entity.id is not None else None,
        entity_type=entity.entity_type,
        entity_id=str(entity.entity_id),
        action=entity.action.value,
        performed_by=entity.performed_by,
        reason=entity.reason,
        timestamp=entity.timestamp,
        previous_value=entity.previous_value,
        new_value=entity.new_value,
        employee_pin=entity.employee_pin,
    )


# ============================================================================
# ScheduleAssignment Mappers
# ============================================================================
def schedule_assignment_to_domain(model: ScheduleAssignmentModel) -> EmployeeScheduleAssignment:
    """Convierte un ScheduleAssignmentModel a EmployeeScheduleAssignment del dominio."""
    working_weekdays = (
        {Weekday(d) for d in model.working_weekdays}
        if model.working_weekdays is not None
        else None
    )
    return EmployeeScheduleAssignment(
        id=model.id,
        employee_pin=model.employee_pin,
        mode=AssignmentMode(model.mode),
        valid_from=model.valid_from,
        valid_until=model.valid_until,
        working_weekdays=working_weekdays,
        shift_definition_id=model.shift_definition_id,
        rotation_pattern_id=model.rotation_pattern_id,
        expected_min_sessions=model.expected_min_sessions,
    )


def schedule_assignment_to_model(
    entity: EmployeeScheduleAssignment,
) -> ScheduleAssignmentModel:
    """Convierte EmployeeScheduleAssignment a ScheduleAssignmentModel."""
    working_weekdays = (
        [w.value for w in entity.working_weekdays]
        if entity.working_weekdays is not None
        else None
    )
    return ScheduleAssignmentModel(
        id=entity.id if entity.id is not None else None,
        employee_pin=entity.employee_pin,
        mode=entity.mode.value,
        valid_from=entity.valid_from,
        valid_until=entity.valid_until,
        working_weekdays=working_weekdays,
        shift_definition_id=entity.shift_definition_id,
        rotation_pattern_id=entity.rotation_pattern_id,
        expected_min_sessions=entity.expected_min_sessions,
    )

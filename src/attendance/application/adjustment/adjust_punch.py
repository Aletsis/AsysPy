"""Casos de uso para ajuste manual de marcaciones con trazabilidad de auditoría."""

from datetime import datetime

from attendance.domain.audit import AuditAction, AuditLog
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.device import AttendanceLog, AuthMethod, LogStatus
from attendance.ports.attendance import AttendanceRepository
from attendance.ports.audit import AuditLogRepository


def create_manual_punch(
    employee_pin: str,
    timestamp: datetime,
    performed_by: str,
    reason: str,
    attendance_repo: AttendanceRepository,
    audit_repo: AuditLogRepository,
    device_id: int = 0,
    raw_status: int = 0,
    raw_punch: int = 1,
) -> AttendanceLog:
    """Crea una marcación manual para un empleado y registra el evento de auditoría obligatorio."""
    if not performed_by or not performed_by.strip():
        raise ValidationError("El usuario responsable de la auditoría es obligatorio.")
    if not reason or not reason.strip():
        raise ValidationError("El motivo del ajuste manual es obligatorio.")

    # 1. Crear marcación con método MANUAL y estatus RAW
    record_uid = int(timestamp.timestamp())
    punch = AttendanceLog(
        id=None,
        record_uid=record_uid,
        employee_pin=employee_pin,
        device_id=device_id,
        timestamp=timestamp,
        raw_status=raw_status,
        raw_punch=raw_punch,
        auth_method=AuthMethod.MANUAL,
        processing_status=LogStatus.RAW,
    )
    attendance_repo.save_raw_log(punch)

    # 2. Registrar trazabilidad de auditoría
    audit = AuditLog(
        id=None,
        entity_type="attendance_log",
        entity_id=punch.id or 0,
        action=AuditAction.PUNCH_CREATED,
        performed_by=performed_by,
        reason=reason,
        timestamp=datetime.now(),
        previous_value=None,
        new_value={
            "employee_pin": employee_pin,
            "timestamp": timestamp.isoformat(),
            "auth_method": AuthMethod.MANUAL.value,
            "device_id": device_id,
        },
        employee_pin=employee_pin,
    )
    audit_repo.save(audit)

    return punch


def modify_punch_timestamp(
    log_id: int,
    new_timestamp: datetime,
    performed_by: str,
    reason: str,
    attendance_repo: AttendanceRepository,
    audit_repo: AuditLogRepository,
) -> AttendanceLog:
    """Modifica la fecha y hora de una marcación existente y registra la auditoría."""
    if not performed_by or not performed_by.strip():
        raise ValidationError("El usuario responsable de la auditoría es obligatorio.")
    if not reason or not reason.strip():
        raise ValidationError("El motivo del ajuste manual es obligatorio.")

    log = attendance_repo.get_by_id(log_id)
    if log is None:
        raise ValidationError(f"Marcación con ID {log_id} no encontrada.")

    old_timestamp = log.timestamp
    old_status = log.processing_status

    # 1. Actualizar datos de la marcación y restablecer a RAW para reevaluar
    log.timestamp = new_timestamp
    log.processing_status = LogStatus.RAW
    attendance_repo.update_log(log)

    # 2. Registrar trazabilidad de auditoría
    audit = AuditLog(
        id=None,
        entity_type="attendance_log",
        entity_id=log_id,
        action=AuditAction.PUNCH_UPDATED,
        performed_by=performed_by,
        reason=reason,
        timestamp=datetime.now(),
        previous_value={
            "timestamp": old_timestamp.isoformat(),
            "processing_status": old_status.value,
        },
        new_value={
            "timestamp": new_timestamp.isoformat(),
            "processing_status": LogStatus.RAW.value,
        },
        employee_pin=log.employee_pin,
    )
    audit_repo.save(audit)

    return log


def cancel_punch(
    log_id: int,
    performed_by: str,
    reason: str,
    attendance_repo: AttendanceRepository,
    audit_repo: AuditLogRepository,
) -> AttendanceLog:
    """Anula una marcación marcándola como IGNORED y registra la auditoría."""
    if not performed_by or not performed_by.strip():
        raise ValidationError("El usuario responsable de la auditoría es obligatorio.")
    if not reason or not reason.strip():
        raise ValidationError("El motivo del ajuste manual es obligatorio.")

    log = attendance_repo.get_by_id(log_id)
    if log is None:
        raise ValidationError(f"Marcación con ID {log_id} no encontrada.")

    old_status = log.processing_status
    log.processing_status = LogStatus.IGNORED
    attendance_repo.update_log(log)

    audit = AuditLog(
        id=None,
        entity_type="attendance_log",
        entity_id=log_id,
        action=AuditAction.PUNCH_DELETED,
        performed_by=performed_by,
        reason=reason,
        timestamp=datetime.now(),
        previous_value={"processing_status": old_status.value},
        new_value={"processing_status": LogStatus.IGNORED.value},
        employee_pin=log.employee_pin,
    )
    audit_repo.save(audit)

    return log

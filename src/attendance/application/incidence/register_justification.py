"""Casos de uso para registro y gestión de incidencias, justificaciones y permisos."""

from datetime import date, time

from attendance.domain.common.exceptions import ValidationError
from attendance.domain.incidence import (
    Justification,
    JustificationStatus,
    JustificationType,
)
from attendance.ports.incidence import IncidenceRepository
from attendance.ports.organization import EmployeeRepository


def register_justification(
    employee_pin: str,
    justification_type: JustificationType,
    start_date: date,
    end_date: date,
    reason: str,
    incidence_repo: IncidenceRepository,
    employee_repo: EmployeeRepository | None = None,
    approved_by: str | None = None,
    support_document: str | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> Justification:
    """Registra una justificación formal (vacaciones, incapacidad IMSS, permisos con/sin goce)."""
    # 1. Validar existencia del empleado si se provee el repositorio
    if employee_repo is not None:
        employee = employee_repo.get_by_pin(employee_pin)
        if employee is None:
            raise ValidationError(f"No existe ningún empleado registrado con el PIN '{employee_pin}'.")

    # 2. Instanciar la entidad (sus invariantes validarán fechas y motivo)
    justification = Justification(
        id=None,
        employee_pin=employee_pin,
        type=justification_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        approved_by=approved_by,
        status=JustificationStatus.APPROVED,
        support_document=support_document,
        start_time=start_time,
        end_time=end_time,
    )

    # 3. Guardar en el repositorio
    return incidence_repo.save(justification)


def cancel_justification(
    justification_id: int,
    incidence_repo: IncidenceRepository,
) -> Justification:
    """Cancela una justificación previamente registrada."""
    justification = incidence_repo.get_by_id(justification_id)
    if justification is None:
        raise ValidationError(f"Justificación con ID {justification_id} no encontrada.")

    justification.status = JustificationStatus.CANCELLED
    return incidence_repo.save(justification)

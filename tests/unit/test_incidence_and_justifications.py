"""Pruebas unitarias para Casos de Uso de Incidencias, Justificaciones y Permisos."""

from datetime import date, time

import pytest

from attendance.adapters.memory import (
    InMemoryEmployeeRepository,
    InMemoryIncidenceRepository,
)
from attendance.application.incidence import (
    cancel_justification,
    register_justification,
)
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.incidence import (
    JustificationStatus,
    JustificationType,
)
from attendance.domain.organization import Employee, Sex


def make_employee(pin: str = "1001") -> Employee:
    return Employee(
        id=1,
        pin=pin,
        first_name="Carlos",
        paternal_last_name="Ramirez",
        maternal_last_name="Silva",
        hire_date=date(2024, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        position="Analista",
        home_branch_id=1,
        active=True,
    )


def test_register_vacation_success():
    emp = make_employee("1001")
    emp_repo = InMemoryEmployeeRepository([emp])
    incidence_repo = InMemoryIncidenceRepository()

    justification = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.VACATION,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 15),
        reason="Vacaciones de Semana Santa",
        incidence_repo=incidence_repo,
        employee_repo=emp_repo,
        approved_by="director_rh",
    )

    assert justification.id is not None
    assert justification.status == JustificationStatus.APPROVED
    assert justification.type == JustificationType.VACATION
    assert justification.approved_by == "director_rh"
    assert justification.is_full_day is True

    # Verificar persistencia y consulta por fecha
    active = incidence_repo.get_active_justification("1001", date(2026, 4, 10))
    assert active is not None
    assert active.reason == "Vacaciones de Semana Santa"


def test_register_imss_incapacity_with_folio():
    emp = make_employee("1001")
    emp_repo = InMemoryEmployeeRepository([emp])
    incidence_repo = InMemoryIncidenceRepository()

    justification = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.IMSS_INCAPACITY,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
        reason="Incapacidad médica por riesgo de trabajo",
        incidence_repo=incidence_repo,
        employee_repo=emp_repo,
        approved_by="medico_empresa",
        support_document="FOLIO-IMSS-2026-00451",
    )

    assert justification.support_document == "FOLIO-IMSS-2026-00451"
    assert justification.type == JustificationType.IMSS_INCAPACITY


def test_register_paid_and_unpaid_leave():
    incidence_repo = InMemoryIncidenceRepository()

    paid = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.PAID_LEAVE,
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
        reason="Permiso por paternidad",
        incidence_repo=incidence_repo,
    )
    assert paid.type == JustificationType.PAID_LEAVE

    unpaid = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.UNPAID_LEAVE,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        reason="Asuntos personales sin goce",
        incidence_repo=incidence_repo,
    )
    assert unpaid.type == JustificationType.UNPAID_LEAVE


def test_validation_error_on_inverted_dates():
    incidence_repo = InMemoryIncidenceRepository()

    with pytest.raises(ValidationError, match="no puede ser anterior a la fecha inicio"):
        register_justification(
            employee_pin="1001",
            justification_type=JustificationType.VACATION,
            start_date=date(2026, 4, 15),
            end_date=date(2026, 4, 10),  # Invertida
            reason="Fechas erróneas",
            incidence_repo=incidence_repo,
        )


def test_validation_error_on_empty_reason():
    incidence_repo = InMemoryIncidenceRepository()

    with pytest.raises(ValidationError, match="motivo.*no puede estar vacío"):
        register_justification(
            employee_pin="1001",
            justification_type=JustificationType.OTHER,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 1),
            reason="   ",
            incidence_repo=incidence_repo,
        )


def test_validation_error_on_non_existent_employee():
    emp_repo = InMemoryEmployeeRepository([])  # Vacío
    incidence_repo = InMemoryIncidenceRepository()

    with pytest.raises(ValidationError, match="No existe ningún empleado"):
        register_justification(
            employee_pin="9999",
            justification_type=JustificationType.VACATION,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
            reason="Vacaciones",
            incidence_repo=incidence_repo,
            employee_repo=emp_repo,
        )


def test_partial_day_permission_by_hours():
    incidence_repo = InMemoryIncidenceRepository()

    perm = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.PAID_LEAVE,
        start_date=date(2026, 4, 10),
        end_date=date(2026, 4, 10),
        reason="Pase de salida cita médica",
        incidence_repo=incidence_repo,
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    assert perm.is_full_day is False
    assert perm.start_time == time(14, 0)
    assert perm.end_time == time(16, 0)

    # Invalidez si hora fin es menor o igual a hora inicio
    with pytest.raises(ValidationError, match="hora de inicio de permiso debe ser menor a la hora de fin"):
        register_justification(
            employee_pin="1001",
            justification_type=JustificationType.PAID_LEAVE,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 10),
            reason="Horas inválidas",
            incidence_repo=incidence_repo,
            start_time=time(16, 0),
            end_time=time(14, 0),
        )


def test_cancel_justification():
    incidence_repo = InMemoryIncidenceRepository()

    j = register_justification(
        employee_pin="1001",
        justification_type=JustificationType.VACATION,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 5),
        reason="Vacaciones canceladas",
        incidence_repo=incidence_repo,
    )
    assert j.id is not None
    assert j.status == JustificationStatus.APPROVED

    cancelled = cancel_justification(j.id, incidence_repo)
    assert cancelled.status == JustificationStatus.CANCELLED

    # No debe aparecer como activa para la fecha
    active = incidence_repo.get_active_justification("1001", date(2026, 4, 2))
    assert active is None

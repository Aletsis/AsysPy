"""Pruebas unitarias para validaciones e invariantes de la entidad Position y relaciones N:M con Department."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from attendance.adapters.memory.in_memory_department_repo import InMemoryDepartmentRepository
from attendance.adapters.memory.in_memory_position_repo import InMemoryPositionRepository
from attendance.adapters.persistence.sql.models import Base
from attendance.adapters.persistence.sql.repositories.department_repo import (
    SqlDepartmentRepository,
)
from attendance.adapters.persistence.sql.repositories.position_repo import (
    SqlPositionRepository,
)
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position


def _make_valid_position(**kwargs) -> Position:
    """Helper para instanciar Position válida con valores predeterminados."""
    defaults = {
        "id": 1,
        "name": "Operador de Planta",
        "code": "POS-01",
        "active": True,
    }
    defaults.update(kwargs)
    return Position(**defaults)


# ============================================================================
# Pruebas de inicialización y normalización de Position
# ============================================================================
def test_position_valid_creation():
    pos = _make_valid_position(
        name="  Supervisor de Turno  ",
        code="  sup-01  ",
        description="  Supervisa las operaciones en planta.  ",
    )
    assert pos.name == "Supervisor de Turno"
    assert pos.code == "SUP-01"
    assert pos.description == "Supervisa las operaciones en planta."
    assert pos.active is True
    assert pos.id == 1

    # Alias en español
    assert pos.nombre == "Supervisor de Turno"
    assert pos.codigo == "SUP-01"
    assert pos.descripcion == "Supervisa las operaciones en planta."
    assert pos.activo is True


def test_position_minimal_creation():
    pos = Position(name="  Analista de Calidad  ")
    assert pos.name == "Analista de Calidad"
    assert pos.code is None
    assert pos.description is None
    assert pos.id is None
    assert pos.active is True

    # Alias
    assert pos.nombre == "Analista de Calidad"
    assert pos.codigo is None
    assert pos.descripcion is None
    assert pos.activo is True


def test_position_spanish_property_setters():
    pos = _make_valid_position()
    pos.nombre = "  Gerente Operativo  "
    pos.codigo = "  ger-01  "
    pos.descripcion = "  Lidera la operación global.  "
    pos.activo = False

    assert pos.name == "Gerente Operativo"
    assert pos.code == "GER-01"
    assert pos.description == "Lidera la operación global."
    assert pos.active is False


# ============================================================================
# Pruebas de validación e invariantes
# ============================================================================
@pytest.mark.parametrize("invalid_desc", ["D" * 501])
def test_position_invalid_description(invalid_desc):
    with pytest.raises(ValidationError):
        _make_valid_position(description=invalid_desc)

@pytest.mark.parametrize("invalid_id", [0, -1, "1", True, False])
def test_position_invalid_id(invalid_id):
    with pytest.raises(ValidationError):
        _make_valid_position(id=invalid_id)


@pytest.mark.parametrize("invalid_name", ["", "   ", "P" * 101])
def test_position_invalid_name(invalid_name):
    with pytest.raises(ValidationError):
        _make_valid_position(name=invalid_name)


@pytest.mark.parametrize("invalid_code", ["", "   ", "C" * 31, "POS 01", "POS\t01"])
def test_position_invalid_code(invalid_code):
    with pytest.raises(ValidationError):
        _make_valid_position(code=invalid_code)


@pytest.mark.parametrize("invalid_active", ["true", 1, 0, None])
def test_position_invalid_active(invalid_active):
    with pytest.raises(ValidationError):
        _make_valid_position(active=invalid_active)


# ============================================================================
# Pruebas de Persistencia SQL y Relaciones N:M
# ============================================================================
def test_sql_position_repository_crud_and_many_to_many():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    pos_repo = SqlPositionRepository(session_factory)
    dept_repo = SqlDepartmentRepository(session_factory)

    # 1. Crear departamentos
    dept_almacen = dept_repo.save(Department(name="Almacén", code="ALM"))
    dept_produccion = dept_repo.save(Department(name="Producción", code="PROD"))
    dept_rrhh = dept_repo.save(Department(name="Recursos Humanos", code="RRHH"))

    # 2. Crear puestos
    p_gral = pos_repo.save(Position(name="Empleado General", code="GEN-01"))
    p_rec = pos_repo.save(Position(name="Reclutador", code="REC-01"))
    p_inact = pos_repo.save(Position(name="Puesto Inactivo", code="INA-01", active=False))

    assert p_gral.id is not None
    assert p_rec.id is not None
    assert p_inact.id is not None

    # 3. Asignaciones N:M
    # Empleado General está tanto en Almacén como en Producción
    dept_repo.assign_position(dept_almacen.id, p_gral.id)
    dept_repo.assign_position(dept_produccion.id, p_gral.id)

    # Reclutador solo está en RRHH
    dept_repo.assign_position(dept_rrhh.id, p_rec.id)

    # Puesto inactivo en Almacén
    dept_repo.assign_position(dept_almacen.id, p_inact.id)

    # Asignación idempotente (no duplica ni falla)
    dept_repo.assign_position(dept_almacen.id, p_gral.id)

    # 4. Consultar puestos por departamento
    almacen_positions = dept_repo.get_positions(dept_almacen.id)
    assert len(almacen_positions) == 2
    assert {p.code for p in almacen_positions} == {"GEN-01", "INA-01"}

    almacen_active_positions = dept_repo.get_positions(dept_almacen.id, active_only=True)
    assert len(almacen_active_positions) == 1
    assert almacen_active_positions[0].code == "GEN-01"

    produccion_positions = dept_repo.get_positions(dept_produccion.id)
    assert len(produccion_positions) == 1
    assert produccion_positions[0].code == "GEN-01"

    rrhh_positions = dept_repo.get_positions(dept_rrhh.id)
    assert len(rrhh_positions) == 1
    assert rrhh_positions[0].code == "REC-01"

    # 5. Consultar departamentos por puesto
    gral_depts = pos_repo.get_departments(p_gral.id)
    assert len(gral_depts) == 2
    assert {d.code for d in gral_depts} == {"ALM", "PROD"}

    rec_depts = pos_repo.get_departments(p_rec.id)
    assert len(rec_depts) == 1
    assert rec_depts[0].code == "RRHH"

    # 6. Filtrar puestos en pos_repo.list_all(department_id=...)
    almacen_all = pos_repo.list_all(department_id=dept_almacen.id)
    assert len(almacen_all) == 2

    almacen_active = pos_repo.list_all(department_id=dept_almacen.id, active_only=True)
    assert len(almacen_active) == 1
    assert almacen_active[0].code == "GEN-01"

    # 7. Desvincular puesto
    removed = dept_repo.remove_position(dept_almacen.id, p_gral.id)
    assert removed is True
    assert dept_repo.remove_position(dept_almacen.id, p_gral.id) is False

    assert len(dept_repo.get_positions(dept_almacen.id)) == 1
    assert len(pos_repo.get_departments(p_gral.id)) == 1

    # 8. Cascada / limpieza al eliminar un puesto o departamento
    assert pos_repo.delete(p_rec.id) is True
    assert len(dept_repo.get_positions(dept_rrhh.id)) == 0

    assert dept_repo.delete(dept_produccion.id) is True
    assert len(pos_repo.get_departments(p_gral.id)) == 0


# ============================================================================
# Pruebas de Persistencia En Memoria y Relaciones N:M
# ============================================================================
def test_in_memory_position_repository_crud_and_many_to_many():
    pos_repo = InMemoryPositionRepository()
    dept_repo = InMemoryDepartmentRepository()
    pos_repo.department_repo = dept_repo
    dept_repo.position_repo = pos_repo

    # 1. Guardar departamentos y puestos
    d1 = dept_repo.save(Department(name="Almacén", code="ALM"))
    d2 = dept_repo.save(Department(name="Producción", code="PROD"))
    d3 = dept_repo.save(Department(name="Recursos Humanos", code="RRHH"))

    p1 = pos_repo.save(Position(name="Empleado General", code="GEN-01"))
    p2 = pos_repo.save(Position(name="Reclutador", code="REC-01"))
    p3 = pos_repo.save(Position(name="Inactivo", code="INA-01", active=False))

    assert pos_repo.get_by_id(p1.id).nombre == "Empleado General"
    assert pos_repo.get_by_code("GEN-01") is not None
    assert pos_repo.get_by_code("NO-EXISTE") is None

    # 2. Asignar puestos a departamentos
    dept_repo.assign_position(d1.id, p1.id)
    dept_repo.assign_position(d2.id, p1.id)
    dept_repo.assign_position(d3.id, p2.id)
    dept_repo.assign_position(d1.id, p3.id)

    # 3. Verificar puestos por departamento
    assert len(dept_repo.get_positions(d1.id)) == 2
    assert len(dept_repo.get_positions(d1.id, active_only=True)) == 1
    assert dept_repo.get_positions(d1.id, active_only=True)[0].code == "GEN-01"

    # 4. Verificar departamentos por puesto
    depts_p1 = pos_repo.get_departments(p1.id)
    assert len(depts_p1) == 2
    assert {d.code for d in depts_p1} == {"ALM", "PROD"}

    # 5. Listar puestos filtrando por department_id
    assert len(pos_repo.list_all(department_id=d1.id)) == 2
    assert len(pos_repo.list_all(department_id=d1.id, active_only=True)) == 1
    assert len(pos_repo.list_all(department_id=d2.id)) == 1
    assert len(pos_repo.list_all(department_id=999)) == 0

    # 6. Remover asignación
    assert dept_repo.remove_position(d1.id, p1.id) is True
    assert dept_repo.remove_position(d1.id, p1.id) is False
    assert len(dept_repo.get_positions(d1.id)) == 1
    assert len(pos_repo.get_departments(p1.id)) == 1

    # 7. Borrado y limpieza
    assert pos_repo.delete(p2.id) is True
    assert len(dept_repo.get_positions(d3.id)) == 0

    assert dept_repo.delete(d2.id) is True
    assert len(pos_repo.get_departments(p1.id)) == 0


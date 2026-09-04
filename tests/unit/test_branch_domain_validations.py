"""Pruebas unitarias para validaciones e invariantes de la entidad Branch."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from attendance.adapters.memory.in_memory_branch_repo import InMemoryBranchRepository
from attendance.adapters.persistence.sql.models import Base
from attendance.adapters.persistence.sql.repositories.branch_repo import SqlBranchRepository
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.branch import Branch


def _make_valid_branch(**kwargs) -> Branch:
    """Helper para crear una instancia válida de Branch con valores por defecto."""
    defaults = {
        "id": 1,
        "name": "Sucursal Matriz",
        "code": "MATRIZ",
        "timezone": "America/Mexico_City",
        "active": True,
    }
    defaults.update(kwargs)
    return Branch(**defaults)


# ============================================================================
# Pruebas de inicialización e invariantes básicas
# ============================================================================
def test_branch_valid_creation():
    b = _make_valid_branch(name="  Norte  ", code="  nor-01  ")
    assert b.name == "Norte"
    assert b.code == "NOR-01"
    assert b.active is True
    assert b.email is None
    assert b.phone_number is None
    assert b.correo is None
    assert b.telefono is None


@pytest.mark.parametrize("invalid_name", ["", "   ", "N" * 101])
def test_branch_invalid_name(invalid_name):
    with pytest.raises(ValidationError):
        _make_valid_branch(name=invalid_name)


@pytest.mark.parametrize("invalid_code", ["", "   ", "C" * 31, "CODE 01", "C\t01"])
def test_branch_invalid_code(invalid_code):
    with pytest.raises(ValidationError):
        _make_valid_branch(code=invalid_code)


@pytest.mark.parametrize("invalid_id", [0, -1, "1", True])
def test_branch_invalid_id(invalid_id):
    with pytest.raises(ValidationError):
        _make_valid_branch(id=invalid_id)


@pytest.mark.parametrize("invalid_tz", ["", "   "])
def test_branch_invalid_timezone(invalid_tz):
    with pytest.raises(ValidationError):
        _make_valid_branch(timezone=invalid_tz)


# ============================================================================
# Pruebas para Correo Electrónico (email / correo)
# ============================================================================
def test_branch_valid_email():
    b = _make_valid_branch(email="  Contacto.Sucursal@Empresa.com  ")
    assert b.email == "contacto.sucursal@empresa.com"
    assert b.correo == "contacto.sucursal@empresa.com"

    # Modificar vía alias
    b.correo = "nueva.sucursal@dominio.mx"
    assert b.email == "nueva.sucursal@dominio.mx"


@pytest.mark.parametrize("invalid_email", [
    "",
    "   ",
    "plainaddress",
    "@missingusername.com",
    "username@.com",
    "username@domain",
    "username@domain..com",
    "user name@domain.com",
    "a" * 250 + "@test.com",
])
def test_branch_invalid_email(invalid_email):
    with pytest.raises(ValidationError):
        _make_valid_branch(email=invalid_email)


# ============================================================================
# Pruebas para Teléfono (phone_number / telefono)
# ============================================================================
@pytest.mark.parametrize("valid_phone, expected_clean", [
    ("5512345678", "5512345678"),
    ("+52 55 1234 5678", "+52 55 1234 5678"),
    ("(33) 9876-5432", "(33) 9876-5432"),
    (" +5215512345678 ", "+5215512345678"),
])
def test_branch_valid_phone(valid_phone, expected_clean):
    b = _make_valid_branch(phone_number=valid_phone)
    assert b.phone_number == expected_clean.strip()
    assert b.telefono == expected_clean.strip()

    b.telefono = "5599887766"
    assert b.phone_number == "5599887766"


@pytest.mark.parametrize("invalid_phone", [
    "",
    "   ",
    "123456789",          # 9 dígitos (muy corto)
    "1234567890123456",  # 16 dígitos (muy largo)
    "55-1234-ABCD",      # contiene letras
    "tel#5512345678",    # caracteres inválidos
])
def test_branch_invalid_phone(invalid_phone):
    with pytest.raises(ValidationError):
        _make_valid_branch(phone_number=invalid_phone)


# ============================================================================
# Pruebas de Persistencia con email y phone_number (SQL y Memoria)
# ============================================================================
def test_sql_branch_repository_persists_email_and_phone():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    repo = SqlBranchRepository(session_factory)

    b = _make_valid_branch(
        id=None,
        code="SUC-SQL",
        name="Sucursal SQL",
        email="sucursal.sql@empresa.com",
        phone_number="+52 55 1122 3344",
    )
    saved = repo.save(b)
    assert saved.id is not None
    assert saved.email == "sucursal.sql@empresa.com"
    assert saved.phone_number == "+52 55 1122 3344"

    loaded = repo.get_by_id(saved.id)
    assert loaded is not None
    assert loaded.email == "sucursal.sql@empresa.com"
    assert loaded.phone_number == "+52 55 1122 3344"

    # Actualizar contacto
    loaded.correo = "contacto.actualizado@empresa.com"
    loaded.telefono = "5599001122"
    repo.save(loaded)

    reloaded = repo.get_by_code("SUC-SQL")
    assert reloaded is not None
    assert reloaded.email == "contacto.actualizado@empresa.com"
    assert reloaded.phone_number == "5599001122"


def test_in_memory_branch_repository_persists_email_and_phone():
    repo = InMemoryBranchRepository()
    b = _make_valid_branch(
        id=None,
        code="SUC-MEM",
        name="Sucursal Memoria",
        email="memoria@empresa.com",
        phone_number="5544332211",
    )
    saved = repo.save(b)
    assert saved.id is not None
    assert saved.correo == "memoria@empresa.com"
    assert saved.telefono == "5544332211"

    loaded = repo.get_by_id(saved.id)
    assert loaded is not None
    assert loaded.email == "memoria@empresa.com"
    assert loaded.phone_number == "5544332211"

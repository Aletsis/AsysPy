"""Pruebas unitarias para las validaciones e invariantes de la entidad Employee y Fingerprint."""

from datetime import date
import pytest

from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.organization.fingerprint import Fingerprint


def _make_valid_employee(**kwargs) -> Employee:
    """Helper para crear una instancia válida de Employee con valores por defecto."""
    defaults = {
        "id": 1,
        "pin": "EMP001",
        "first_name": "Juan Carlos",
        "paternal_last_name": "Pérez",
        "maternal_last_name": "Hernández",
        "hire_date": date(2023, 1, 15),
        "sex": Sex.MALE,
        "department_id": 1,
        "position": "Operador General",
        "home_branch_id": 1,
        "active": True,
    }
    defaults.update(kwargs)
    return Employee(**defaults)


# ============================================================================
# Pruebas para Fingerprint Value Object
# ============================================================================
def test_fingerprint_valid_creation():
    fp = Fingerprint(finger_index=0, template="dGVtcGxhdGVfZGF0YQ==", algorithm_version="10.0")
    assert fp.finger_index == 0
    assert fp.template == "dGVtcGxhdGVfZGF0YQ=="
    assert fp.algorithm_version == "10.0"
    assert fp.valid is True


@pytest.mark.parametrize("invalid_index", [-1, 10, "0", True, 2.5])
def test_fingerprint_invalid_index(invalid_index):
    with pytest.raises(ValidationError):
        Fingerprint(finger_index=invalid_index, template="valid_template")


@pytest.mark.parametrize("invalid_template", ["", "   ", None])
def test_fingerprint_empty_template(invalid_template):
    with pytest.raises(ValidationError):
        Fingerprint(finger_index=1, template=invalid_template)


def test_fingerprint_empty_algorithm():
    with pytest.raises(ValidationError):
        Fingerprint(finger_index=1, template="valid_template", algorithm_version="")


# ============================================================================
# Pruebas para atributos existentes e invariantes de Employee
# ============================================================================
def test_employee_valid_basic_creation():
    emp = _make_valid_employee()
    assert emp.full_name == "Juan Carlos Pérez Hernández"
    assert emp.pin == "EMP001"
    assert emp.active is True


@pytest.mark.parametrize("invalid_pin", ["", "   ", "EMP 001", "EMP\t01", "A" * 51])
def test_employee_invalid_pin(invalid_pin):
    with pytest.raises(ValidationError):
        _make_valid_employee(pin=invalid_pin)


@pytest.mark.parametrize("invalid_name", ["", "   ", "A" * 101])
def test_employee_invalid_name(invalid_name):
    with pytest.raises(ValidationError):
        _make_valid_employee(first_name=invalid_name)


@pytest.mark.parametrize("invalid_paternal", ["", "   ", "A" * 101])
def test_employee_invalid_paternal_last_name(invalid_paternal):
    with pytest.raises(ValidationError):
        _make_valid_employee(paternal_last_name=invalid_paternal)


def test_employee_maternal_last_name_optional_and_normalized():
    emp = _make_valid_employee(maternal_last_name="   ")
    assert emp.maternal_last_name is None
    assert emp.full_name == "Juan Carlos Pérez"

    with pytest.raises(ValidationError):
        _make_valid_employee(maternal_last_name="M" * 101)


def test_employee_invalid_hire_date():
    with pytest.raises(ValidationError):
        _make_valid_employee(hire_date="2023-01-01")


def test_employee_sex_string_auto_conversion():
    emp = _make_valid_employee(sex="female")
    assert emp.sex == Sex.FEMALE

    with pytest.raises(ValidationError):
        _make_valid_employee(sex="otro")


@pytest.mark.parametrize("invalid_dept", [0, -1, "1", False])
def test_employee_invalid_department_id(invalid_dept):
    with pytest.raises(ValidationError):
        _make_valid_employee(department_id=invalid_dept)


@pytest.mark.parametrize("invalid_branch", [0, -2, "2", True])
def test_employee_invalid_home_branch_id(invalid_branch):
    with pytest.raises(ValidationError):
        _make_valid_employee(home_branch_id=invalid_branch)


@pytest.mark.parametrize("invalid_pos", ["", "   ", "P" * 101])
def test_employee_invalid_position(invalid_pos):
    with pytest.raises(ValidationError):
        _make_valid_employee(position=invalid_pos)


@pytest.mark.parametrize("invalid_active", ["true", 1, 0, None])
def test_employee_invalid_active(invalid_active):
    with pytest.raises(ValidationError):
        _make_valid_employee(active=invalid_active)


# ============================================================================
# Pruebas para Correo Electrónico (email / correo)
# ============================================================================
def test_employee_valid_email():
    emp = _make_valid_employee(email="  Juan.Perez@Empresa.com  ")
    assert emp.email == "juan.perez@empresa.com"
    assert emp.correo == "juan.perez@empresa.com"

    # Modificar vía alias
    emp.correo = "nuevo.correo@dominio.org"
    assert emp.email == "nuevo.correo@dominio.org"


@pytest.mark.parametrize("invalid_email", [
    "",
    "   ",
    "plainaddress",
    "@missingusername.com",
    "username@.com",
    "username@domain",
    "username@domain..com",
    "user name@domain.com",
    "a" * 250 + "@test.com",  # Excede 255
])
def test_employee_invalid_email(invalid_email):
    with pytest.raises(ValidationError):
        _make_valid_employee(email=invalid_email)


# ============================================================================
# Pruebas para Número Telefónico (phone_number / telefono)
# ============================================================================
@pytest.mark.parametrize("valid_phone, expected_clean", [
    ("5512345678", "5512345678"),
    ("+52 55 1234 5678", "+52 55 1234 5678"),
    ("(55) 1234-5678", "(55) 1234-5678"),
    (" +5215512345678 ", "+5215512345678"),
])
def test_employee_valid_phone(valid_phone, expected_clean):
    emp = _make_valid_employee(phone_number=valid_phone)
    assert emp.phone_number == expected_clean.strip()
    assert emp.telefono == expected_clean.strip()

    emp.telefono = "5599887766"
    assert emp.phone_number == "5599887766"


@pytest.mark.parametrize("invalid_phone", [
    "",
    "   ",
    "123456789",          # 9 dígitos (muy corto)
    "1234567890123456",  # 16 dígitos (muy largo)
    "55-1234-ABCD",      # contiene letras
    "phone#5512345678",  # caracteres inválidos
])
def test_employee_invalid_phone(invalid_phone):
    with pytest.raises(ValidationError):
        _make_valid_employee(phone_number=invalid_phone)


# ============================================================================
# Pruebas para CURP
# ============================================================================
def test_employee_valid_curp():
    # CURP válida según RENAPO
    emp = _make_valid_employee(curp="  pehj850412hdfrmn03  ")
    assert emp.curp == "PEHJ850412HDFRMN03"


@pytest.mark.parametrize("invalid_curp", [
    "",
    "   ",
    "PEHJ850412HDFRMN0",    # 17 caracteres
    "PEHJ850412HDFRMN031",  # 19 caracteres
    "1EHJ850412HDFRMN03",   # Empieza con número
    "PEHJ850412XDFRMN03",   # Sexo 'X' inválido (debe ser H o M)
    "PEHJ850412HXXRMN03",   # Estado 'XX' inexistente en México
    "PEHJ850412HDF11N03",   # Consonantes internas reemplazadas por números
])
def test_employee_invalid_curp(invalid_curp):
    with pytest.raises(ValidationError):
        _make_valid_employee(curp=invalid_curp)


# ============================================================================
# Pruebas para RFC
# ============================================================================
def test_employee_valid_rfc():
    emp = _make_valid_employee(rfc="  pehj850412ab1  ")
    assert emp.rfc == "PEHJ850412AB1"


@pytest.mark.parametrize("invalid_rfc", [
    "",
    "   ",
    "PEHJ850412AB",    # 12 caracteres (persona moral, empleado debe ser física 13)
    "PEHJ850412AB12",  # 14 caracteres
    "1EHJ850412AB1",   # Empieza con número
    "PEHJ85041AAB1",   # Fecha con letra
])
def test_employee_invalid_rfc(invalid_rfc):
    with pytest.raises(ValidationError):
        _make_valid_employee(rfc=invalid_rfc)


# ============================================================================
# Pruebas para Contraseña de Checador (password / contrasena)
# ============================================================================
@pytest.mark.parametrize("valid_pass", ["1", "1234", "12345678"])
def test_employee_valid_password(valid_pass):
    emp = _make_valid_employee(password=valid_pass)
    assert emp.password == valid_pass
    assert emp.contrasena == valid_pass

    emp.contrasena = "87654321"
    assert emp.password == "87654321"


@pytest.mark.parametrize("invalid_pass", [
    "",
    "   ",
    "123456789",  # > 8 dígitos (límite de teclado en reloj checador)
    "abcd",       # No numérica
    "12a4",       # Caracteres alfanuméricos no soportados en teclado numérico
])
def test_employee_invalid_password(invalid_pass):
    with pytest.raises(ValidationError):
        _make_valid_employee(password=invalid_pass)


# ============================================================================
# Pruebas para Tarjeta RFID (card_number / tarjeta)
# ============================================================================
@pytest.mark.parametrize("valid_card", [
    "0009876543",
    "12345",
    "A1B2C3D4",
    "CARD0000000000000001",  # 20 caracteres
])
def test_employee_valid_card_number(valid_card):
    emp = _make_valid_employee(card_number=valid_card)
    assert emp.card_number == valid_card
    assert emp.tarjeta == valid_card

    emp.tarjeta = "9988776655"
    assert emp.card_number == "9988776655"


@pytest.mark.parametrize("invalid_card", [
    "",
    "   ",
    "1234 5678",              # Espacios internos
    "CARD00000000000000001",  # 21 caracteres (>20)
    "CARD#123",               # Caracteres no alfanuméricos
])
def test_employee_invalid_card_number(invalid_card):
    with pytest.raises(ValidationError):
        _make_valid_employee(card_number=invalid_card)


# ============================================================================
# Pruebas para Huellas Biométricas (fingerprints / huellas)
# ============================================================================
def test_employee_fingerprints_management():
    emp = _make_valid_employee()
    assert emp.fingerprints == []
    assert emp.huellas == []

    # Agregar huellas
    fp0 = Fingerprint(finger_index=0, template="template_index_0")
    fp1 = Fingerprint(finger_index=1, template="template_index_1")
    emp.add_fingerprint(fp0)
    emp.add_fingerprint(fp1)

    assert len(emp.fingerprints) == 2
    assert emp.get_fingerprint(0) == fp0
    assert emp.get_fingerprint(1) == fp1
    assert emp.get_fingerprint(2) is None

    # Reemplazar plantilla para el mismo dedo
    fp0_v2 = Fingerprint(finger_index=0, template="template_index_0_updated")
    emp.add_fingerprint(fp0_v2)
    assert len(emp.fingerprints) == 2
    assert emp.get_fingerprint(0) == fp0_v2

    # Eliminar huella
    assert emp.remove_fingerprint(1) is True
    assert len(emp.fingerprints) == 1
    assert emp.get_fingerprint(1) is None
    assert emp.remove_fingerprint(1) is False


def test_employee_fingerprints_duplicate_detection_on_init():
    fp0 = Fingerprint(finger_index=0, template="template_1")
    fp0_dup = Fingerprint(finger_index=0, template="template_2")

    with pytest.raises(ValidationError, match="Existe más de una huella registrada para el dedo con índice 0"):
        _make_valid_employee(fingerprints=[fp0, fp0_dup])


def test_employee_fingerprints_maximum_10():
    fps = [Fingerprint(finger_index=i, template=f"template_{i}") for i in range(10)]
    emp = _make_valid_employee(fingerprints=fps)
    assert len(emp.fingerprints) == 10

    # Reemplazar una huella existente sigue funcionando con 10 huellas
    fp9_nuevo = Fingerprint(finger_index=9, template="template_9_nuevo")
    emp.add_fingerprint(fp9_nuevo)
    assert len(emp.fingerprints) == 10
    assert emp.get_fingerprint(9) == fp9_nuevo

    # Intentar asignar una lista con más de 10 huellas
    with pytest.raises(ValidationError, match="Un empleado no puede tener más de 10 huellas"):
        emp.huellas = fps + [Fingerprint(0, "extra")]

    # Intentar asignar elemento que no es Fingerprint
    with pytest.raises(ValidationError, match="Cada elemento de la lista de huellas debe ser una instancia de Fingerprint"):
        emp.huellas = [Fingerprint(0, "t"), "no_es_fingerprint"]  # type: ignore

    # Intentar agregar huella no instancia
    with pytest.raises(ValidationError, match="El objeto a agregar debe ser una instancia de Fingerprint"):
        emp.add_fingerprint("invalido")  # type: ignore


# ============================================================================
# Pruebas de persistencia (SQL y Memoria) con los nuevos atributos y huellas
# ============================================================================
def test_sql_employee_repository_with_all_new_fields_and_fingerprints():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from attendance.adapters.persistence.sql.models import Base
    from attendance.adapters.persistence.sql.repositories.employee_repo import SqlEmployeeRepository

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    repo = SqlEmployeeRepository(session_factory)

    emp = _make_valid_employee(
        id=None,
        pin="EMP_FULL",
        first_name="María",
        paternal_last_name="López",
        maternal_last_name="García",
        email="maria.lopez@empresa.com",
        phone_number="+52 55 1234 5678",
        curp="LOGM850412MDFRRN09",
        rfc="LOGM850412AB1",
        password="1234",
        card_number="CARD001",
        fingerprints=[
            Fingerprint(finger_index=0, template="tmpl_0"),
            Fingerprint(finger_index=6, template="tmpl_6"),
        ],
    )
    saved = repo.save(emp)
    assert saved.id is not None

    loaded = repo.get_by_pin("EMP_FULL")
    assert loaded is not None
    assert loaded.email == "maria.lopez@empresa.com"
    assert loaded.phone_number == "+52 55 1234 5678"
    assert loaded.curp == "LOGM850412MDFRRN09"
    assert loaded.rfc == "LOGM850412AB1"
    assert loaded.password == "1234"
    assert loaded.card_number == "CARD001"
    assert len(loaded.fingerprints) == 2
    fp0 = loaded.get_fingerprint(0)
    fp6 = loaded.get_fingerprint(6)
    assert fp0 is not None and fp0.template == "tmpl_0"
    assert fp6 is not None and fp6.template == "tmpl_6"

    # Actualizar campos y huellas
    loaded.email = "maria.actualizada@empresa.com"
    loaded.password = "87654321"
    assert loaded.remove_fingerprint(0) is True
    loaded.add_fingerprint(Fingerprint(finger_index=7, template="tmpl_7"))
    repo.save(loaded)

    reloaded = repo.get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.email == "maria.actualizada@empresa.com"
    assert reloaded.password == "87654321"
    assert len(reloaded.fingerprints) == 2
    assert reloaded.get_fingerprint(0) is None
    assert reloaded.get_fingerprint(6) is not None
    assert reloaded.get_fingerprint(7) is not None

    # Eliminar
    assert repo.delete("EMP_FULL") is True
    assert repo.get_by_pin("EMP_FULL") is None
    assert repo.get_by_id(saved.id) is None


def test_in_memory_employee_repository_preserves_new_fields():
    from attendance.adapters.memory.in_memory_employee_repo import InMemoryEmployeeRepository

    repo = InMemoryEmployeeRepository()
    emp = _make_valid_employee(
        id=None,
        pin="EMP_MEM",
        email="mem@empresa.com",
        phone_number="5512345678",
        curp="LOGM850412MDFRRN09",
        rfc="LOGM850412AB1",
        password="4321",
        card_number="CARD_MEM_1",
        fingerprints=[Fingerprint(finger_index=2, template="mem_template")],
    )
    saved = repo.save(emp)
    assert saved.id is not None

    fetched = repo.get_by_pin("EMP_MEM")
    assert fetched is not None
    assert fetched.correo == "mem@empresa.com"
    assert fetched.telefono == "5512345678"
    assert fetched.curp == "LOGM850412MDFRRN09"
    assert fetched.rfc == "LOGM850412AB1"
    assert fetched.contrasena == "4321"
    assert fetched.tarjeta == "CARD_MEM_1"
    assert len(fetched.huellas) == 1
    assert fetched.get_fingerprint(2).template == "mem_template"

"""Pruebas de integración para la persistencia del catálogo de empleados (EmployeeRepository)."""

from datetime import date

from attendance.adapters.memory.in_memory_employee_repo import InMemoryEmployeeRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.organization.fingerprint import Fingerprint


def test_in_memory_employee_repo_full_crud() -> None:
    repo = InMemoryEmployeeRepository()

    # Create (mínimo con obligatorios y defaults)
    e1 = Employee(
        pin="EMP001",
        first_name="Carlos",
        paternal_last_name="García",
        sex=Sex.MALE,
        department_id=1,
        position_id=10,
        home_branch_id=2,
        curp="GARC800101HDFRRN01",
        rfc="GARC800101AB1",
        card_number="CARD_01",
        email="carlos.garcia@empresa.com",
    )
    saved1 = repo.save(e1)
    assert saved1.id == 1
    assert saved1.hire_date == date.today()
    assert saved1.position_id == 10

    # Read por diferentes identificadores
    assert repo.get_by_id(1) is not None
    assert repo.get_by_pin("EMP001") is not None
    assert repo.get_by_curp("garc800101hdfrrn01") is not None
    assert repo.get_by_rfc("garc800101ab1") is not None
    assert repo.get_by_card_number("CARD_01") is not None
    assert repo.get_by_email("Carlos.Garcia@Empresa.com") is not None

    # Verificación de existencia
    assert repo.exists_by_pin("EMP001") is True
    assert repo.exists_by_pin("NOEXISTE") is False
    assert repo.exists_by_id(1) is True
    assert repo.exists_by_id(999) is False

    # Update
    saved1.first_name = "Carlos Alberto"
    saved1.position_id = 12
    saved1.active = False
    repo.save(saved1)

    updated = repo.get_by_id(1)
    assert updated is not None
    assert updated.first_name == "Carlos Alberto"
    assert updated.position_id == 12
    assert updated.active is False

    # Batch save_all y filtrado en list_all / count
    e2 = Employee(
        pin="EMP002",
        first_name="Ana",
        paternal_last_name="Martínez",
        sex=Sex.FEMALE,
        department_id=2,
        position_id=10,
        home_branch_id=2,
        active=True,
    )
    e3 = Employee(
        pin="EMP003",
        first_name="Beatriz",
        paternal_last_name="Alvarez",
        sex=Sex.FEMALE,
        department_id=1,
        position_id=15,
        home_branch_id=3,
        active=True,
    )
    repo.save_all([e2, e3])

    assert repo.count() == 3
    assert repo.count(active_only=True) == 2
    assert repo.count(branch_id=2) == 2
    assert repo.count(branch_id=2, active_only=True) == 1
    assert repo.count(department_id=1) == 2
    assert repo.count(position_id=10) == 1
    assert repo.count(position_id=12) == 1

    # list_all ordenado por apellido y nombre
    all_emps = repo.list_all()
    assert [e.paternal_last_name for e in all_emps] == ["Alvarez", "García", "Martínez"]

    # Delete por ID
    assert repo.delete_by_id(1) is True
    assert repo.get_by_id(1) is None
    assert repo.exists_by_id(1) is False
    assert repo.delete_by_id(999) is False

    # Delete por PIN
    assert repo.delete("EMP002") is True
    assert repo.get_by_pin("EMP002") is None
    assert repo.delete("EMP002") is False
    assert repo.count() == 1


def test_sql_employee_repo_full_crud() -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )
    repo = bundle.employee_repo

    # Create con huellas y todos los campos
    fp1 = Fingerprint(finger_index=0, template="tpl_dedo_0")
    fp2 = Fingerprint(finger_index=1, template="tpl_dedo_1")
    emp1 = Employee(
        pin="SQL_001",
        first_name="Diana",
        paternal_last_name="Sánchez",
        maternal_last_name="Ruiz",
        sex=Sex.FEMALE,
        department_id=5,
        position_id=20,
        home_branch_id=1,
        active=True,
        curp="SARD900101MDFRNN05",
        rfc="SARD900101XY1",
        card_number="CARD_SQL_1",
        email="diana.sanchez@empresa.com",
        fingerprints=[fp1, fp2],
    )
    saved = repo.save(emp1)
    assert saved.id is not None
    assert saved.hire_date == date.today()
    assert saved.position_id == 20
    assert len(saved.fingerprints) == 2

    # Read por diferentes identificadores
    assert repo.get_by_id(saved.id) is not None
    assert repo.get_by_pin("SQL_001") is not None
    assert repo.get_by_curp("SARD900101MDFRNN05") is not None
    assert repo.get_by_rfc("SARD900101XY1") is not None
    assert repo.get_by_card_number("CARD_SQL_1") is not None
    assert repo.get_by_email("Diana.Sanchez@Empresa.com") is not None

    # Verificación de existencia
    assert repo.exists_by_pin("SQL_001") is True
    assert repo.exists_by_pin("NOEXISTE") is False
    assert repo.exists_by_id(saved.id) is True
    assert repo.exists_by_id(99999) is False

    # Actualizar empleado y huellas
    saved.position_id = 25
    saved.email = "diana.nueva@empresa.com"
    saved.remove_fingerprint(0)
    saved.add_fingerprint(Fingerprint(finger_index=2, template="tpl_dedo_2"))
    repo.save(saved)

    reloaded = repo.get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.position_id == 25
    assert reloaded.email == "diana.nueva@empresa.com"
    assert len(reloaded.fingerprints) == 2
    assert reloaded.get_fingerprint(0) is None
    assert reloaded.get_fingerprint(1) is not None
    assert reloaded.get_fingerprint(2) is not None

    # Batch save_all y filtros
    emp2 = Employee(
        pin="SQL_002",
        first_name="Esteban",
        paternal_last_name="Torres",
        sex=Sex.MALE,
        department_id=5,
        position_id=20,
        home_branch_id=1,
        active=False,
    )
    emp3 = Employee(
        pin="SQL_003",
        first_name="Fabiola",
        paternal_last_name="Morales",
        sex=Sex.FEMALE,
        department_id=3,
        position_id=20,
        home_branch_id=2,
        active=True,
    )
    repo.save_all([emp2, emp3])

    assert repo.count() == 3
    assert repo.count(active_only=True) == 2
    assert repo.count(department_id=5) == 2
    assert repo.count(position_id=20) == 2
    assert repo.count(branch_id=1, active_only=True) == 1

    # list_all con filtros
    dept5_emps = repo.list_all(department_id=5)
    assert len(dept5_emps) == 2
    assert [e.pin for e in dept5_emps] == ["SQL_001", "SQL_002"]

    active_in_branch1 = repo.list_all(branch_id=1, active_only=True)
    assert len(active_in_branch1) == 1
    assert active_in_branch1[0].pin == "SQL_001"

    # Delete por PIN y verificar limpieza de huellas
    assert repo.delete("SQL_001") is True
    assert repo.get_by_pin("SQL_001") is None
    assert repo.get_by_id(saved.id) is None
    assert repo.delete("SQL_001") is False

    # Delete por ID
    emp3_db = repo.get_by_pin("SQL_003")
    assert emp3_db is not None
    assert repo.delete_by_id(emp3_db.id) is True
    assert repo.get_by_pin("SQL_003") is None
    assert repo.delete_by_id(99999) is False

    assert repo.count() == 1

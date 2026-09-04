"""Pruebas de integración para la persistencia del catálogo de puestos (PositionRepository)."""

from attendance.adapters.memory.in_memory_department_repo import InMemoryDepartmentRepository
from attendance.adapters.memory.in_memory_position_repo import InMemoryPositionRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.department import Department
from attendance.domain.organization.position import Position


def test_in_memory_position_repo_full_crud() -> None:
    dept_repo = InMemoryDepartmentRepository()
    repo = InMemoryPositionRepository(department_repo=dept_repo)
    dept_repo.position_repo = repo

    # 1. Create (mínimo solo con name, y con todos los campos)
    p1 = Position(name="Operador de Planta")
    p2 = Position(
        name="Ingeniero de Procesos",
        code="ING-01",
        description="Supervisión de líneas productivas",
        active=True,
    )
    saved1 = repo.save(p1)
    saved2 = repo.save(p2)

    assert saved1.id == 1
    assert saved1.code is None
    assert saved1.description is None
    assert saved1.active is True

    assert saved2.id == 2
    assert saved2.code == "ING-01"
    assert saved2.description == "Supervisión de líneas productivas"

    # 2. Read / Identificadores
    assert repo.get_by_id(1) is not None
    assert repo.get_by_id(999) is None
    assert repo.get_by_code("ing-01") is not None
    assert repo.get_by_code("NOEXISTE") is None
    assert repo.get_by_name("operador de planta") is not None
    assert repo.get_by_name("No Existe") is None

    # 3. Verificación de existencia
    assert repo.exists_by_id(1) is True
    assert repo.exists_by_id(999) is False
    assert repo.exists_by_code("ING-01") is True
    assert repo.exists_by_code("NOEXISTE") is False

    # 4. Update
    saved1.name = "Operador Senior de Planta"
    saved1.code = "OP-SR"
    saved1.description = "Operador con certificación avanzada"
    saved1.active = False
    repo.save(saved1)

    updated = repo.get_by_id(1)
    assert updated is not None
    assert updated.name == "Operador Senior de Planta"
    assert updated.code == "OP-SR"
    assert updated.description == "Operador con certificación avanzada"
    assert updated.active is False

    # 5. Batch save_all y counts / list_all
    p3 = Position(name="Director de Finanzas", code="DIR-FIN", active=True)
    p4 = Position(name="Auxiliar Contable", code="AUX-CON", active=True)
    repo.save_all([p3, p4])

    assert repo.count() == 4
    assert repo.count(active_only=True) == 3

    # list_all ordenado por nombre insensible a mayúsculas
    all_positions = repo.list_all()
    assert [p.name for p in all_positions] == [
        "Auxiliar Contable",
        "Director de Finanzas",
        "Ingeniero de Procesos",
        "Operador Senior de Planta",
    ]

    # 6. Relaciones N:M con Department
    dept1 = dept_repo.save(Department(name="Producción", code="PROD"))
    dept2 = dept_repo.save(Department(name="Calidad", code="CAL"))

    repo.assign_department(saved2.id, dept1.id)
    repo.assign_department(saved2.id, dept2.id)
    # Idempotente
    repo.assign_department(saved2.id, dept1.id)

    depts = repo.get_departments(saved2.id)
    assert len(depts) == 2
    assert {d.name for d in depts} == {"Producción", "Calidad"}

    # Filtrado por department_id
    assert repo.count(department_id=dept1.id) == 1
    assert len(repo.list_all(department_id=dept1.id)) == 1
    assert repo.list_all(department_id=dept1.id)[0].name == "Ingeniero de Procesos"

    # Desasignación
    assert repo.remove_department(saved2.id, dept1.id) is True
    assert repo.remove_department(saved2.id, dept1.id) is False
    assert len(repo.get_departments(saved2.id)) == 1

    # 7. Delete
    assert repo.delete(1) is True
    assert repo.get_by_id(1) is None
    assert repo.exists_by_id(1) is False
    assert repo.delete(999) is False
    assert repo.count() == 3


def test_sql_position_repo_full_crud() -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )
    repo = bundle.position_repo
    dept_repo = bundle.department_repo
    assert repo is not None

    # 1. Create (mínimo solo con name, y con todos los campos)
    p1 = Position(name="Operador de Ensamble")
    p2 = Position(
        name="Líder de Calidad",
        code="CAL-LDR",
        description="Lidera aseguramiento de calidad en planta",
        active=True,
    )
    saved1 = repo.save(p1)
    saved2 = repo.save(p2)

    assert saved1.id is not None
    assert saved1.code is None
    assert saved1.description is None
    assert saved1.active is True

    assert saved2.id is not None
    assert saved2.code == "CAL-LDR"
    assert saved2.description == "Lidera aseguramiento de calidad en planta"

    # 2. Read / Identificadores
    assert repo.get_by_id(saved1.id) is not None
    assert repo.get_by_id(99999) is None
    assert repo.get_by_code("cal-ldr") is not None
    assert repo.get_by_code("NOEXISTE") is None
    assert repo.get_by_name("operador de ensamble") is not None
    assert repo.get_by_name("No Existe") is None

    # 3. Verificación de existencia
    assert repo.exists_by_id(saved1.id) is True
    assert repo.exists_by_id(99999) is False
    assert repo.exists_by_code("CAL-LDR") is True
    assert repo.exists_by_code("NOEXISTE") is False

    # 4. Update
    saved1.name = "Operador Senior de Ensamble"
    saved1.code = "OP-ENS-SR"
    saved1.description = "Especialista en ensamble electromecánico"
    saved1.active = False
    repo.save(saved1)

    updated = repo.get_by_id(saved1.id)
    assert updated is not None
    assert updated.name == "Operador Senior de Ensamble"
    assert updated.code == "OP-ENS-SR"
    assert updated.description == "Especialista en ensamble electromecánico"
    assert updated.active is False

    # 5. Batch save_all y counts / list_all
    p3 = Position(name="Abogado Corporativo", code="ABO-CORP", active=True)
    p4 = Position(name="Asistente Legal", code="ASI-LEG", active=True)
    repo.save_all([p3, p4])

    assert repo.count() == 4
    assert repo.count(active_only=True) == 3

    # list_all ordenado por nombre insensible a mayúsculas
    all_positions = repo.list_all()
    assert [p.name for p in all_positions] == [
        "Abogado Corporativo",
        "Asistente Legal",
        "Líder de Calidad",
        "Operador Senior de Ensamble",
    ]

    # 6. Relaciones N:M con Department
    dept1 = dept_repo.save(Department(name="Legal", code="LEG"))
    dept2 = dept_repo.save(Department(name="Dirección", code="DIR"))

    p3_db = repo.get_by_code("ABO-CORP")
    assert p3_db is not None
    repo.assign_department(p3_db.id, dept1.id)
    repo.assign_department(p3_db.id, dept2.id)
    # Idempotente
    repo.assign_department(p3_db.id, dept1.id)

    depts = repo.get_departments(p3_db.id)
    assert len(depts) == 2
    assert {d.name for d in depts} == {"Legal", "Dirección"}

    # Filtrado por department_id
    assert repo.count(department_id=dept1.id) == 1
    assert len(repo.list_all(department_id=dept1.id)) == 1
    assert repo.list_all(department_id=dept1.id)[0].name == "Abogado Corporativo"

    # Desasignación
    assert repo.remove_department(p3_db.id, dept1.id) is True
    assert repo.remove_department(p3_db.id, dept1.id) is False
    assert len(repo.get_departments(p3_db.id)) == 1

    # 7. Delete
    assert repo.delete(saved1.id) is True
    assert repo.get_by_id(saved1.id) is None
    assert repo.exists_by_id(saved1.id) is False
    assert repo.delete(99999) is False
    assert repo.count() == 3

"""Pruebas de integración para la persistencia de sucursales (BranchRepository)."""

from attendance.adapters.memory.in_memory_branch_repo import InMemoryBranchRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.address import Address
from attendance.domain.organization.branch import Branch


def test_in_memory_branch_repo_crud() -> None:
    repo = InMemoryBranchRepository()

    # 1. Create (mínimo con name y code, y con todos los atributos)
    b_min = Branch(name="Sucursal Periférico", code="PERI-01")
    saved_min = repo.save(b_min)
    assert saved_min.id == 1
    assert saved_min.code == "PERI-01"
    assert saved_min.timezone == "America/Mexico_City"
    assert saved_min.active is True

    b1 = Branch(
        name="Matriz",
        code="MAT-01",
        timezone="America/Mexico_City",
        email="matriz@empresa.com",
        phone_number="5511223344",
        active=True,
    )
    saved = repo.save(b1)
    assert saved.id == 2
    assert saved.code == "MAT-01"

    # 2. Get por ID, Código y Nombre (case-insensitive)
    assert repo.get_by_id(saved.id) is not None
    assert repo.get_by_id(999) is None
    assert repo.get_by_code("mat-01") is not None
    assert repo.get_by_code("NONEXISTENT") is None
    assert repo.get_by_name("matriz") is not None
    assert repo.get_by_name("sucursal periférico") is not None
    assert repo.get_by_name("No Existe") is None

    # 3. Verificación de existencia
    assert repo.exists_by_id(saved.id) is True
    assert repo.exists_by_id(999) is False
    assert repo.exists_by_code("MAT-01") is True
    assert repo.exists_by_code("NONEXISTENT") is False

    # 4. Update
    saved.name = "Sucursal Principal Matriz"
    saved.active = False
    repo.save(saved)

    updated = repo.get_by_id(saved.id)
    assert updated is not None
    assert updated.name == "Sucursal Principal Matriz"
    assert updated.active is False

    # 5. Batch save_all y counts / list_all
    b2 = Branch(name="Norte", code="NOR-01", active=True)
    b3 = Branch(name="Occidente", code="OCC-01", active=True)
    repo.save_all([b2, b3])

    assert repo.count() == 4
    assert repo.count(active_only=True) == 3

    # list_all ordenado alfabéticamente por nombre
    all_branches = repo.list_all()
    assert [b.name for b in all_branches] == [
        "Norte",
        "Occidente",
        "Sucursal Periférico",
        "Sucursal Principal Matriz",
    ]

    # 6. Delete
    assert repo.delete(saved_min.id) is True
    assert repo.get_by_id(saved_min.id) is None
    assert repo.exists_by_id(saved_min.id) is False
    assert repo.delete(999) is False
    assert repo.count() == 3


def test_sql_branch_repo_crud() -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )
    repo = bundle.branch_repo
    assert repo is not None

    # 1. Create (mínimo con name y code, y con Address completa)
    b_min = Branch(name="Sucursal Vallejo", code="VAL-01")
    saved_min = repo.save(b_min)
    assert saved_min.id is not None
    assert saved_min.code == "VAL-01"
    assert saved_min.timezone == "America/Mexico_City"

    addr = Address(
        street="Av. Reforma",
        exterior_number="222",
        interior_number="Piso 5",
        postal_code="06600",
        neighborhood="Juárez",
        municipality="Cuauhtémoc",
        state="CDMX",
    )
    b1 = Branch(
        name="Reforma",
        code="REF-01",
        address=addr,
        timezone="America/Mexico_City",
        email="reforma@empresa.com",
        phone_number="+52 55 9988 7766",
        active=True,
    )
    saved = repo.save(b1)
    assert saved.id is not None
    assert saved.code == "REF-01"

    # 2. Get por ID, Código y Nombre
    found = repo.get_by_id(saved.id)
    assert found is not None
    assert found.name == "Reforma"
    assert found.address is not None
    assert found.address.street == "Av. Reforma"
    assert found.address.municipality == "Cuauhtémoc"

    by_code = repo.get_by_code("ref-01")
    assert by_code is not None
    assert by_code.id == saved.id

    by_name = repo.get_by_name("reforma")
    assert by_name is not None
    assert by_name.id == saved.id
    assert repo.get_by_name("sucursal vallejo") is not None
    assert repo.get_by_name("Inexistente") is None

    # 3. Verificación de existencia
    assert repo.exists_by_id(saved.id) is True
    assert repo.exists_by_id(99999) is False
    assert repo.exists_by_code("REF-01") is True
    assert repo.exists_by_code("NONEXISTENT") is False

    # 4. Update
    found.name = "Torre Reforma"
    found.active = False
    repo.save(found)

    reloaded = repo.get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.name == "Torre Reforma"
    assert reloaded.active is False

    # 5. Batch save_all y counts / list_all
    b2 = Branch(name="Guadalajara", code="GDL-01", active=True)
    b3 = Branch(name="Monterrey", code="MTY-01", active=True)
    repo.save_all([b2, b3])

    assert repo.count() == 4
    assert repo.count(active_only=True) == 3

    # list_all ordenado por nombre insensible a mayúsculas
    all_branches = repo.list_all()
    assert [b.name for b in all_branches] == [
        "Guadalajara",
        "Monterrey",
        "Sucursal Vallejo",
        "Torre Reforma",
    ]

    # 6. Delete
    assert repo.delete(saved.id) is True
    assert repo.get_by_id(saved.id) is None
    assert repo.exists_by_id(saved.id) is False
    assert repo.delete(99999) is False
    assert repo.count() == 3


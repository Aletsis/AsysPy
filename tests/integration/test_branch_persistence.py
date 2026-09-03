"""Pruebas de integración para la persistencia de sucursales (BranchRepository)."""

from attendance.adapters.memory.in_memory_branch_repo import InMemoryBranchRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.address import Address
from attendance.domain.organization.branch import Branch


def test_in_memory_branch_repo_crud() -> None:
    repo = InMemoryBranchRepository()

    # Create
    b1 = Branch(name="Matriz", code="MAT-01", timezone="America/Mexico_City")
    saved = repo.save(b1)
    assert saved.id == 1
    assert saved.code == "MAT-01"

    # Get by ID and Code
    assert repo.get_by_id(1) is not None
    assert repo.get_by_code("MAT-01") is not None
    assert repo.get_by_code("NONEXISTENT") is None

    # Update
    saved.name = "Sucursal Principal Matriz"
    saved.active = False
    repo.save(saved)

    updated = repo.get_by_id(1)
    assert updated is not None
    assert updated.name == "Sucursal Principal Matriz"
    assert updated.active is False

    # List all
    b2 = Branch(name="Norte", code="NOR-01", active=True)
    repo.save(b2)
    assert len(repo.list_all()) == 2
    assert len(repo.list_all(active_only=True)) == 1

    # Delete
    assert repo.delete(1) is True
    assert repo.get_by_id(1) is None
    assert repo.delete(999) is False


def test_sql_branch_repo_crud() -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )
    repo = bundle.branch_repo

    # Create with Address
    addr = Address(
        street="Av. Reforma",
        exterior_number="222",
        interior_number="Piso 5",
        postal_code="06600",
        neighborhood="Juárez",
        municipality="Cuauhtémoc",
        state="CDMX",
    )
    b1 = Branch(name="Reforma", code="REF-01", address=addr, timezone="America/Mexico_City", active=True)
    saved = repo.save(b1)
    assert saved.id is not None
    assert saved.code == "REF-01"

    # Get by ID and Code
    found = repo.get_by_id(saved.id)
    assert found is not None
    assert found.name == "Reforma"
    assert found.address is not None
    assert found.address.street == "Av. Reforma"
    assert found.address.municipality == "Cuauhtémoc"

    by_code = repo.get_by_code("REF-01")
    assert by_code is not None
    assert by_code.id == saved.id

    # Update
    found.name = "Torre Reforma"
    found.active = False
    repo.save(found)

    reloaded = repo.get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.name == "Torre Reforma"
    assert reloaded.active is False

    # List all
    b2 = Branch(name="Guadalajara", code="GDL-01", active=True)
    repo.save(b2)
    assert len(repo.list_all()) == 2
    assert len(repo.list_all(active_only=True)) == 1

    # Delete
    assert repo.delete(saved.id) is True
    assert repo.get_by_id(saved.id) is None
    assert repo.delete(999) is False

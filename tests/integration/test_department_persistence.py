"""Pruebas de integración para la persistencia de departamentos (DepartmentRepository)."""

from attendance.adapters.memory.in_memory_department_repo import InMemoryDepartmentRepository
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.department import Department


def test_in_memory_department_repo_crud() -> None:
    repo = InMemoryDepartmentRepository()

    # Create
    d1 = Department(name="Recursos Humanos", code="RH-01")
    saved = repo.save(d1)
    assert saved.id == 1
    assert saved.code == "RH-01"

    # Get by ID and Code
    assert repo.get_by_id(1) is not None
    assert repo.get_by_code("RH-01") is not None
    assert repo.get_by_code("NONEXISTENT") is None

    # Update
    saved.name = "Capital Humano"
    saved.active = False
    repo.save(saved)

    updated = repo.get_by_id(1)
    assert updated is not None
    assert updated.name == "Capital Humano"
    assert updated.active is False

    # List all
    d2 = Department(name="Producción", code="PRD-01", branch_id=2, active=True)
    repo.save(d2)
    assert len(repo.list_all()) == 2
    assert len(repo.list_all(active_only=True)) == 1
    assert len(repo.list_all(branch_id=2)) == 1

    # Delete
    assert repo.delete(1) is True
    assert repo.get_by_id(1) is None
    assert repo.delete(999) is False


def test_sql_department_repo_crud() -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )
    repo = bundle.department_repo

    # Create
    d1 = Department(name="Sistemas", code="TI-01", branch_id=1, active=True)
    saved = repo.save(d1)
    assert saved.id is not None
    assert saved.code == "TI-01"

    # Get by ID and Code
    found = repo.get_by_id(saved.id)
    assert found is not None
    assert found.name == "Sistemas"
    assert found.branch_id == 1

    by_code = repo.get_by_code("TI-01")
    assert by_code is not None
    assert by_code.id == saved.id

    # Update
    found.name = "Tecnologías de Información"
    found.active = False
    repo.save(found)

    reloaded = repo.get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.name == "Tecnologías de Información"
    assert reloaded.active is False

    # List all
    d2 = Department(name="Finanzas", code="FIN-01", branch_id=2, active=True)
    repo.save(d2)
    assert len(repo.list_all()) == 2
    assert len(repo.list_all(active_only=True)) == 1
    assert len(repo.list_all(branch_id=2)) == 1

    # Delete
    assert repo.delete(saved.id) is True
    assert repo.get_by_id(saved.id) is None
    assert repo.delete(999) is False

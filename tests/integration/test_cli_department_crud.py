"""Pruebas de integración para los comandos CRUD de department en la CLI de AsistPy."""

from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory


def test_cli_department_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True)
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Add
        code = main(["department", "add", "--name", "Recursos Humanos", "--code", "RH-01", "--branch-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "registrado exitosamente" in out
        assert "RH-01" in out

        # Add duplicate code should fail
        code = main(["department", "add", "--name", "Otro RH", "--code", "RH-01"])
        assert code == 1
        capsys.readouterr()

        # 2. Show by code
        code = main(["department", "show", "--code", "RH-01"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Recursos Humanos" in out
        assert "RH-01" in out

        # Show by ID
        code = main(["department", "show", "--department-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Recursos Humanos" in out

        # 3. List
        code = main(["department", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "RH-01" in out
        assert "Total departamentos: 1" in out

        # 4. Edit
        code = main(["department", "edit", "--code", "RH-01", "--name", "Capital Humano", "--inactive"])
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizado exitosamente" in out

        main(["department", "show", "--code", "RH-01"])
        out = capsys.readouterr().out
        assert "Capital Humano" in out
        assert "Inactivo" in out

        # 5. Delete
        code = main(["department", "delete", "--code", "RH-01", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminado correctamente" in out

        # Show should fail
        code = main(["department", "show", "--code", "RH-01"])
        assert code == 1


def test_cli_db_status_with_departments(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True)
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        main(["department", "add", "--name", "Operaciones", "--code", "OPS-01"])
        capsys.readouterr()

        code = main(["db", "status"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Departamentos Registrados" in out
        assert "1" in out

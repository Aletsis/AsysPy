"""Pruebas de integración para el catálogo de puestos en la CLI de AsistPy."""

from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory


def test_cli_position_crud_and_departments(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True)
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Add
        code = main([
            "position", "add",
            "--name", "Ingeniero de Procesos",
            "--code", "ING-01",
            "--description", "Optimización de procesos de planta",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "registrado exitosamente" in out
        assert "Ingeniero de Procesos" in out

        # Duplicate code should fail
        code = main(["position", "add", "--name", "Otro Puesto", "--code", "ING-01"])
        assert code == 1
        capsys.readouterr()

        # 2. Show
        code = main(["position", "show", "--code", "ING-01"])
        assert code == 0
        show_out = capsys.readouterr().out
        assert "Ingeniero de Procesos" in show_out
        assert "ING-01" in show_out
        assert "Optimización de procesos de planta" in show_out

        # Show by ID
        code = main(["position", "show", "--id", "1"])
        assert code == 0
        assert "Ingeniero de Procesos" in capsys.readouterr().out

        # Show by Name
        code = main(["position", "show", "--name", "Ingeniero de Procesos"])
        assert code == 0
        assert "ING-01" in capsys.readouterr().out

        # 3. List
        code = main(["position", "list"])
        assert code == 0
        list_out = capsys.readouterr().out
        assert "ING-01" in list_out
        assert "Total puestos: 1" in list_out

        # 4. Asignar a departamento
        main(["department", "add", "--name", "Operaciones", "--code", "OP-01"])
        capsys.readouterr()

        # Desde position: assign-department
        code = main(["position", "assign-department", "--position-id", "1", "--department-id", "1"])
        assert code == 0
        assign_out = capsys.readouterr().out
        assert "asignado al departamento" in assign_out

        # Verificar en position show
        main(["position", "show", "--id", "1"])
        show_dept_out = capsys.readouterr().out
        assert "Operaciones (#1)" in show_dept_out

        # Verificar en department show
        main(["department", "show", "--code", "OP-01"])
        dept_show_out = capsys.readouterr().out
        assert "Ingeniero de Procesos (#1)" in dept_show_out

        # 5. Edit
        code = main(["position", "edit", "--code", "ING-01", "--name", "Ingeniero Líder de Procesos", "--inactive"])
        assert code == 0
        edit_out = capsys.readouterr().out
        assert "actualizado exitosamente" in edit_out

        main(["position", "show", "--code", "ING-01"])
        show_after_edit = capsys.readouterr().out
        assert "Ingeniero Líder de Procesos" in show_after_edit
        assert "Inactivo" in show_after_edit

        # 6. Desvincular departamento (remove-position en department)
        code = main(["department", "remove-position", "--code", "OP-01", "--position-id", "1"])
        assert code == 0
        rem_out = capsys.readouterr().out
        assert "desvinculado del departamento" in rem_out

        # 7. Delete
        code = main(["position", "delete", "--code", "ING-01", "--force"])
        assert code == 0
        del_out = capsys.readouterr().out
        assert "eliminado correctamente" in del_out

        # Show should fail
        code = main(["position", "show", "--code", "ING-01"])
        assert code == 1

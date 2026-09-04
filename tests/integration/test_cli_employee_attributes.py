"""Pruebas de integración para la CLI de empleados con los nuevos atributos."""

from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory


def test_cli_employee_new_attributes_and_validations(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True)
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Crear puesto en catálogo para relacionar
        code = main(["position", "add", "--name", "Desarrollador Senior", "--code", "DEV-01"])
        assert code == 0
        capsys.readouterr()

        # 2. Agregar empleado con todos los nuevos atributos válidos
        code = main([
            "employee", "add",
            "--pin", "E500",
            "--first-name", "Roberto",
            "--paternal-last-name", "Gomez",
            "--maternal-last-name", "Bolaños",
            "--hire-date", "2024-01-15",
            "--sex", "male",
            "--position-id", "1",
            "--email", "roberto.gomez@empresa.com",
            "--phone", "+52 33 1234 5678",
            "--curp", "GOBI500115HDFMNR01",
            "--rfc", "GOBI500115ABC",
            "--password", "1234",
            "--card-number", "CARD-9999",
            "--department-id", "1",
            "--branch-id", "1",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Roberto Gomez" in out
        assert "E500" in out
        assert "GOBI500115HDFMNR01" in out
        assert "CARD-9999" in out

        # 3. Consultar detalle completo (show)
        code = main(["employee", "show", "--pin", "E500"])
        assert code == 0
        show_out = capsys.readouterr().out
        assert "roberto.gomez@empresa.com" in show_out
        assert "+52 33 1234 5678" in show_out
        assert "GOBI500115HDFMNR01" in show_out
        assert "GOBI500115ABC" in show_out
        assert "CARD-9999" in show_out
        assert "Desarrollador Senior" in show_out
        assert "********" in show_out

        # Consultar por ID numérico
        code = main(["employee", "show", "--id", "1"])
        assert code == 0
        show_id_out = capsys.readouterr().out
        assert "Roberto Gomez" in show_id_out

        # 4. Modificar atributos (edit)
        code = main([
            "employee", "edit",
            "--pin", "E500",
            "--email", "r.gomez.nuevo@empresa.com",
            "--phone", "+52 55 9876 5432",
            "--card-number", "CARD-8888",
        ])
        assert code == 0
        edit_out = capsys.readouterr().out
        assert "actualizado exitosamente" in edit_out

        # Verificar edición
        main(["employee", "show", "--pin", "E500"])
        show_after_edit = capsys.readouterr().out
        assert "r.gomez.nuevo@empresa.com" in show_after_edit
        assert "+52 55 9876 5432" in show_after_edit
        assert "CARD-8888" in show_after_edit

        # 5. Listar con filtros de departamento y puesto
        code = main(["employee", "list", "--position-id", "1", "--department-id", "1"])
        assert code == 0
        list_out = capsys.readouterr().out
        assert "E500" in list_out
        assert "Total empleados: 1" in list_out

        # Filtro con resultado vacío
        code = main(["employee", "list", "--position-id", "99"])
        assert code == 0
        list_empty_out = capsys.readouterr().out
        assert "No se encontraron empleados" in list_empty_out

        # 6. Validaciones de dominio fallidas (captura de ValidationError amigable)
        # Email inválido
        code = main([
            "employee", "add",
            "--pin", "E501",
            "--first-name", "Test",
            "--paternal-last-name", "Invalido",
            "--email", "correo-sin-arroba",
        ])
        assert code == 1
        err_out = capsys.readouterr().err
        assert "Error de validación" in err_out

        # CURP inválida
        code = main([
            "employee", "add",
            "--pin", "E502",
            "--first-name", "Test",
            "--paternal-last-name", "Invalido",
            "--curp", "CURPINCORRECTA123",
        ])
        assert code == 1
        err_curp = capsys.readouterr().err
        assert "Error de validación" in err_curp

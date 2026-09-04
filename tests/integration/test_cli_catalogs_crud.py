"""Pruebas de integración para los comandos CRUD de catálogos en la CLI de AsistPy."""

from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory


def test_cli_branch_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Add
        code = main(
            [
                "branch",
                "add",
                "--name",
                "Sucursal Centro",
                "--code",
                "CEN-01",
                "--city",
                "Monterrey",
                "--state",
                "NL",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "registrada exitosamente" in out
        assert "CEN-01" in out

        # 2. Show
        code = main(["branch", "show", "--code", "CEN-01"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Sucursal Centro" in out
        assert "Monterrey, NL" in out

        # 3. List
        code = main(["branch", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "CEN-01" in out
        assert "Total sucursales: 1" in out

        # 4. Edit
        code = main(
            [
                "branch",
                "edit",
                "--code",
                "CEN-01",
                "--name",
                "Sucursal Centro Histórico",
                "--inactive",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizada exitosamente" in out

        # Check in show
        main(["branch", "show", "--code", "CEN-01"])
        out = capsys.readouterr().out
        assert "Sucursal Centro Histórico" in out
        assert "Inactivo" in out

        # 5. Delete
        code = main(["branch", "delete", "--code", "CEN-01", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminada correctamente" in out

        # Show should fail
        code = main(["branch", "show", "--code", "CEN-01"])
        assert code == 1


def test_cli_employee_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # Setup positions
        main(["position", "add", "--name", "Supervisora", "--code", "SUP-01"])
        main(["position", "add", "--name", "Gerente de Planta", "--code", "GER-01"])
        capsys.readouterr()

        # 1. Add
        code = main(
            [
                "employee",
                "add",
                "--pin",
                "E200",
                "--first-name",
                "Laura",
                "--paternal-last-name",
                "Martinez",
                "--maternal-last-name",
                "Soto",
                "--hire-date",
                "2025-06-01",
                "--sex",
                "female",
                "--position-id",
                "1",
                "--department-id",
                "2",
                "--branch-id",
                "1",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "registrado exitosamente" in out
        assert "E200" in out

        # Add duplicate should fail
        code = main(
            [
                "employee",
                "add",
                "--pin",
                "E200",
                "--first-name",
                "Laura",
                "--paternal-last-name",
                "Martinez",
            ]
        )
        assert code == 1
        capsys.readouterr()

        # 2. Show
        code = main(["employee", "show", "--pin", "E200"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Laura Martinez Soto" in out
        assert "Supervisora" in out

        # 3. List
        code = main(["employee", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "E200" in out
        assert "Total empleados: 1" in out

        # 4. Edit
        code = main(["employee", "edit", "--pin", "E200", "--position-id", "2", "--inactive"])
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizado exitosamente" in out

        main(["employee", "show", "--pin", "E200"])
        out = capsys.readouterr().out
        assert "Gerente de Planta" in out
        assert "Inactivo" in out

        # 5. Delete
        code = main(["employee", "delete", "--pin", "E200", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminado correctamente" in out

        # Show should fail
        code = main(["employee", "show", "--pin", "E200"])
        assert code == 1


def test_cli_shift_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Add
        code = main(
            [
                "shift",
                "add",
                "--name",
                "Turno Nocturno",
                "--start-time",
                "22:00",
                "--end-time",
                "06:00",
                "--tolerance",
                "10",
                "--crosses-midnight",
                "--category",
                "nocturno",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "Turno Nocturno" in out
        assert "registrado exitosamente" in out

        # 2. Show
        code = main(["shift", "show", "--shift-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Turno Nocturno" in out
        assert "22:00:00" in out
        assert "06:00:00" in out
        assert "Sí" in out

        # 3. List
        code = main(["shift", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Turno Nocturno" in out
        assert "Total turnos: 1" in out

        # 4. Edit
        code = main(
            ["shift", "edit", "--shift-id", "1", "--name", "Nocturno Avanzado", "--tolerance", "15"]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizado exitosamente" in out

        main(["shift", "show", "--shift-id", "1"])
        out = capsys.readouterr().out
        assert "Nocturno Avanzado" in out
        assert "15 minutos" in out

        # 5. Delete
        code = main(["shift", "delete", "--shift-id", "1", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminado correctamente" in out

        # Show should fail
        code = main(["shift", "show", "--shift-id", "1"])
        assert code == 1


def test_cli_shift_categories_all(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # Test regular (from CLI manual)
        code = main(
            [
                "shift",
                "add",
                "--name",
                "Matutino 8-16",
                "--start-time",
                "08:00",
                "--end-time",
                "16:00",
                "--tolerance",
                "15",
                "--category",
                "regular",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "Matutino 8-16" in out
        assert "regular" in out

        # Test partido
        code = main(
            [
                "shift",
                "add",
                "--name",
                "Turno Partido",
                "--start-time",
                "09:00",
                "--end-time",
                "18:00",
                "--category",
                "partido",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "Turno Partido" in out
        assert "partido" in out

        # Test matutino
        code = main(
            [
                "shift",
                "add",
                "--name",
                "Turno Matutino Puro",
                "--start-time",
                "06:00",
                "--end-time",
                "14:00",
                "--category",
                "matutino",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "matutino" in out

        # Test edit category
        code = main(["shift", "edit", "--shift-id", "1", "--category", "vespertino"])
        assert code == 0
        capsys.readouterr()

        main(["shift", "show", "--shift-id", "1"])
        show_out = capsys.readouterr().out
        assert "vespertino" in show_out


def test_cli_schedule_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # Setup employee and shift
        main(
            [
                "employee",
                "add",
                "--pin",
                "E300",
                "--first-name",
                "Pedro",
                "--paternal-last-name",
                "Ramirez",
            ]
        )
        main(["shift", "add", "--name", "Matutino", "--start-time", "08:00", "--end-time", "16:00"])
        capsys.readouterr()

        # 1. Assign
        code = main(
            [
                "schedule",
                "assign",
                "--employee-pin",
                "E300",
                "--shift-id",
                "1",
                "--mode",
                "fixed",
                "--valid-from",
                "2026-09-01",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "Horario asignado exitosamente" in out

        # 2. Show
        code = main(["schedule", "show", "--assignment-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "E300" in out
        assert "Matutino" in out

        # 3. List
        code = main(["schedule", "list", "--employee-pin", "E300"])
        assert code == 0
        out = capsys.readouterr().out
        assert "E300" in out
        assert "Total asignaciones: 1" in out

        # 4. Edit
        code = main(["schedule", "edit", "--assignment-id", "1", "--valid-until", "2026-12-31"])
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizada exitosamente" in out

        # 5. Close
        code = main(["schedule", "close", "--assignment-id", "1", "--valid-until", "2026-10-31"])
        assert code == 0
        out = capsys.readouterr().out
        assert "cerrada con vigencia hasta" in out

        # 6. Delete
        code = main(["schedule", "delete", "--assignment-id", "1", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminada correctamente" in out


def test_cli_device_crud(capsys) -> None:
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Add
        code = main(
            [
                "device",
                "add",
                "--name",
                "Reloj Acceso Norte",
                "--ip",
                "192.168.1.150",
                "--port",
                "4370",
                "--branch-id",
                "1",
                "--serial",
                "SN-998877",
                "--location",
                "Caseta Norte",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "registrado exitosamente" in out
        assert "Reloj Acceso Norte" in out

        # 2. Show
        code = main(["device", "show", "--device-id", "1"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Reloj Acceso Norte" in out
        assert "192.168.1.150" in out
        assert "Caseta Norte" in out

        # 3. List
        code = main(["device", "list"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Reloj Acceso Norte" in out
        assert "Total dispositivos: 1" in out

        # 4. Edit
        code = main(
            [
                "device",
                "edit",
                "--device-id",
                "1",
                "--name",
                "Reloj Acceso Norte Renovado",
                "--inactive",
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert "actualizado exitosamente" in out

        main(["device", "show", "--device-id", "1"])
        out = capsys.readouterr().out
        assert "Reloj Acceso Norte Renovado" in out
        assert "Inactivo" in out

        # 5. Delete
        code = main(["device", "delete", "--device-id", "1", "--force"])
        assert code == 0
        out = capsys.readouterr().out
        assert "eliminado correctamente" in out

        # Show should fail
        code = main(["device", "show", "--device-id", "1"])
        assert code == 1


def test_cli_catalogs_full_e2e_flow(capsys) -> None:
    """Flujo completo E2E: sucursal -> empleado -> turno -> horario -> dispositivo -> marcación -> evaluación."""
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # 1. Sucursal
        assert main(["branch", "add", "--name", "Planta Principal", "--code", "PLT-01"]) == 0

        # 2. Empleado
        assert (
            main(
                [
                    "employee",
                    "add",
                    "--pin",
                    "OP100",
                    "--first-name",
                    "Juan",
                    "--paternal-last-name",
                    "Perez",
                    "--branch-id",
                    "1",
                ]
            )
            == 0
        )

        # 3. Turno
        assert (
            main(
                [
                    "shift",
                    "add",
                    "--name",
                    "Diurno",
                    "--start-time",
                    "08:00",
                    "--end-time",
                    "16:00",
                    "--tolerance",
                    "15",
                ]
            )
            == 0
        )

        # 4. Asignar horario
        assert (
            main(
                [
                    "schedule",
                    "assign",
                    "--employee-pin",
                    "OP100",
                    "--shift-id",
                    "1",
                    "--valid-from",
                    "2026-09-01",
                ]
            )
            == 0
        )

        # 5. Dispositivo
        assert main(["device", "add", "--name", "Reloj Planta", "--ip", "192.168.1.100"]) == 0

        # 6. Registrar marcaciones manuales (ajuste con auditoría)
        assert (
            main(
                [
                    "attendance",
                    "adjust",
                    "--employee-pin",
                    "OP100",
                    "--timestamp",
                    "2026-09-02 08:05:00",
                    "--reason",
                    "Entrada en caseta",
                    "--modified-by",
                    "admin",
                ]
            )
            == 0
        )
        assert (
            main(
                [
                    "attendance",
                    "adjust",
                    "--employee-pin",
                    "OP100",
                    "--timestamp",
                    "2026-09-02 16:02:00",
                    "--reason",
                    "Salida normal",
                    "--modified-by",
                    "admin",
                ]
            )
            == 0
        )

        # 7. Evaluar jornada del empleado
        capsys.readouterr()
        assert (
            main(["attendance", "evaluate", "--employee-pin", "OP100", "--date", "2026-09-02"]) == 0
        )
        out = capsys.readouterr().out
        assert "OP100" in out
        assert "PRESENTE" in out
        assert "Diurno" in out

        # 8. Reporte consolidado
        assert (
            main(["report", "summary", "--start-date", "2026-09-01", "--end-date", "2026-09-05"])
            == 0
        )
        report_out = capsys.readouterr().out
        assert "OP100" in report_out
        assert "present" in report_out.lower()

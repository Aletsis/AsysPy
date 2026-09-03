"""Pruebas de integración para la ejecución de comandos de la CLI de AsistPy."""

import json
from datetime import date, datetime, time
from pathlib import Path
from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.device import (
    AttendanceLog,
    AuthMethod,
    LogStatus,
)
from attendance.domain.organization import Employee, Sex
from attendance.domain.schedule import AssignmentMode, EmployeeScheduleAssignment, ShiftDefinition


def test_cli_db_init_and_status(capsys) -> None:
    code_init = main(["db", "init", "--backend", "memory"])
    assert code_init == 0
    captured = capsys.readouterr()
    assert "Repositorios inicializados en memoria" in captured.out

    code_status = main(["db", "status", "--backend", "memory"])
    assert code_status == 0
    captured = capsys.readouterr()
    assert "Motor / Backend" in captured.out
    assert "memory" in captured.out


def test_cli_device_list_empty(capsys) -> None:
    code = main(["device", "list", "--backend", "memory"])
    assert code == 0
    captured = capsys.readouterr()
    assert "No se encontraron dispositivos" in captured.out


def test_cli_attendance_adjust_and_list(capsys) -> None:
    # 1. Crear marcación manual
    code_adjust = main([
        "attendance",
        "adjust",
        "--employee-pin",
        "E-100",
        "--timestamp",
        "2026-09-03 08:00:00",
        "--reason",
        "Ajuste por falla en lector biométrico",
        "--modified-by",
        "supervisor_test",
        "--backend",
        "memory",
    ])
    assert code_adjust == 0
    captured = capsys.readouterr()
    assert "Marcación manual creada exitosamente" in captured.out
    assert "E-100" in captured.out


def test_cli_report_summary_formats(capsys, tmp_path: Path) -> None:
    # Formato JSON
    code_json = main([
        "report",
        "summary",
        "--start-date",
        "2026-09-01",
        "--end-date",
        "2026-09-05",
        "--format",
        "json",
        "--backend",
        "memory",
    ])
    assert code_json == 0
    captured = capsys.readouterr()
    parsed_json = json.loads(captured.out)
    assert isinstance(parsed_json, list)

    # Formato CSV a archivo
    out_file = tmp_path / "test_report.csv"
    code_csv = main([
        "report",
        "summary",
        "--start-date",
        "2026-09-01",
        "--end-date",
        "2026-09-05",
        "--format",
        "csv",
        "--output",
        str(out_file),
        "--backend",
        "memory",
    ])
    assert code_csv == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "employee_pin,date,expected_shift" in content


def test_cli_device_probe_mocked(capsys) -> None:
    with patch("attendance.adapters.cli.commands.device.ZkTcpReader") as mock_reader_cls:
        instance = mock_reader_cls.return_value
        instance.get_device_info.return_value = {"firmware": "Ver 6.60", "serial": "SN12345678"}
        instance.get_raw_logs.return_value = [
            AttendanceLog(
                id=1,
                record_uid=1,
                employee_pin="101",
                device_id=1,
                timestamp=datetime.now(),
                raw_status=0,
                raw_punch=1,
                auth_method=AuthMethod.FINGERPRINT,
                processing_status=LogStatus.RAW,
            )
        ]

        code = main(["device", "probe", "--ip", "192.168.1.50", "--port", "4370", "--backend", "memory"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Conexión exitosa con el reloj biométrico" in captured.out
        assert "Ver 6.60" in captured.out
        assert "SN12345678" in captured.out


def test_cli_device_sync_mocked(capsys) -> None:
    with patch("attendance.adapters.cli.commands.device.ZkTcpReader") as mock_reader_cls:
        instance = mock_reader_cls.return_value
        instance.get_raw_logs.return_value = []

        code = main(["device", "sync", "--ip", "192.168.1.50", "--port", "4370", "--backend", "memory"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Sincronización exitosa" in captured.out


def test_cli_attendance_evaluate_flow(capsys) -> None:
    # Usar sqlite en memoria mediante base de datos dedicada
    bundle = PersistenceFactory.create_bundle(
        backend="sqlite",
        connection_string="sqlite:///:memory:",
        init_tables=True,
    )

    # Registrar empleado
    emp = Employee(
        id=1,
        pin="E100",
        first_name="Carlos",
        paternal_last_name="Gomez",
        maternal_last_name=None,
        hire_date=date(2020, 1, 1),
        sex=Sex.MALE,
        department_id=1,
        position="Operador",
        home_branch_id=1,
        active=True,
    )
    bundle.employee_repo.save(emp)

    # Registrar turno
    shift = ShiftDefinition(
        id=1,
        name="Turno Matutino",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    bundle.shift_repo.save(shift)

    # Asignar turno
    assignment = EmployeeScheduleAssignment(
        id=1,
        employee_pin="E100",
        mode=AssignmentMode.FIXED,
        valid_from=date(2026, 9, 1),
        shift_definition_id=1,
    )
    bundle.schedule_assignment_repo.save(assignment)

    # Parchear para que la CLI use este bundle en memoria configurado
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "attendance",
            "evaluate",
            "--employee-pin",
            "E100",
            "--date",
            "2026-09-02",
        ])
        assert code == 0
        captured = capsys.readouterr()
        assert "E100" in captured.out
        assert "Turno Matutino" in captured.out
        assert "Evaluación completada" in captured.out


def test_cli_no_args_shows_help(capsys) -> None:
    code = main([])
    assert code == 1
    captured = capsys.readouterr()
    assert "AsistPy: Herramienta CLI unificada" in captured.out

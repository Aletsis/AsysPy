"""Pruebas unitarias para el analizador de argumentos de la CLI (parser)."""

import pytest

from attendance.adapters.cli.commands.attendance import (
    _format_minutes,
    _parse_datetime,
)
from attendance.adapters.cli.main import build_parser


def test_build_parser_recognizes_subcommands() -> None:
    parser = build_parser()

    # db subcommands
    args_db_init = parser.parse_args(["db", "init"])
    assert args_db_init.command == "db"
    assert args_db_init.db_action == "init"

    args_db_status = parser.parse_args(["db", "status"])
    assert args_db_status.command == "db"
    assert args_db_status.db_action == "status"

    # device subcommands
    args_device_list = parser.parse_args(["device", "list", "--active-only"])
    assert args_device_list.command == "device"
    assert args_device_list.device_action == "list"
    assert args_device_list.active_only is True

    args_device_probe = parser.parse_args(["device", "probe", "--ip", "10.0.0.1", "--port", "4370"])
    assert args_device_probe.command == "device"
    assert args_device_probe.device_action == "probe"
    assert args_device_probe.ip == "10.0.0.1"
    assert args_device_probe.port == 4370

    # attendance subcommands
    args_att_eval = parser.parse_args([
        "attendance",
        "evaluate",
        "--employee-pin",
        "E001",
        "--date",
        "2026-09-01",
    ])
    assert args_att_eval.command == "attendance"
    assert args_att_eval.attendance_action == "evaluate"
    assert args_att_eval.employee_pin == "E001"

    # report subcommands
    args_rep = parser.parse_args([
        "report",
        "summary",
        "--start-date",
        "2026-09-01",
        "--end-date",
        "2026-09-07",
        "--format",
        "csv",
    ])
    assert args_rep.command == "report"
    assert args_rep.report_action == "summary"
    assert args_rep.format == "csv"

    # position subcommands
    args_pos_add = parser.parse_args([
        "position",
        "add",
        "--name",
        "Analista QA",
        "--code",
        "QA-01",
        "--description",
        "Pruebas de software",
    ])
    assert args_pos_add.command == "position"
    assert args_pos_add.position_action == "add"
    assert args_pos_add.name == "Analista QA"
    assert args_pos_add.code == "QA-01"

    args_pos_list = parser.parse_args(["position", "list", "--department-id", "2", "--active-only"])
    assert args_pos_list.command == "position"
    assert args_pos_list.position_action == "list"
    assert args_pos_list.department_id == 2
    assert args_pos_list.active_only is True

    # employee add with new attributes
    args_emp_add = parser.parse_args([
        "employee",
        "add",
        "--pin",
        "E999",
        "--first-name",
        "Pedro",
        "--paternal-last-name",
        "Perez",
        "--email",
        "pedro@empresa.com",
        "--phone",
        "+523312345678",
        "--curp",
        "PEPE800101HDFRRN09",
        "--rfc",
        "PEPE800101ABC",
        "--password",
        "123456",
        "--card-number",
        "CARD-1234",
        "--position-id",
        "5",
    ])
    assert args_emp_add.command == "employee"
    assert args_emp_add.employee_action == "add"
    assert args_emp_add.email == "pedro@empresa.com"
    assert args_emp_add.phone == "+523312345678"
    assert args_emp_add.curp == "PEPE800101HDFRRN09"
    assert args_emp_add.rfc == "PEPE800101ABC"
    assert args_emp_add.password == "123456"
    assert args_emp_add.card_number == "CARD-1234"
    assert args_emp_add.position_id == 5

    # department assign-position
    args_dept_assign = parser.parse_args([
        "department",
        "assign-position",
        "--department-id",
        "3",
        "--position-id",
        "5",
    ])
    assert args_dept_assign.command == "department"
    assert args_dept_assign.department_action == "assign-position"
    assert args_dept_assign.department_id == 3
    assert args_dept_assign.position_id == 5


def test_global_arguments_both_orders() -> None:
    parser = build_parser()

    # Leading backend
    args1 = parser.parse_args(["--backend", "postgres", "db", "status"])
    assert getattr(args1, "backend", None) == "postgres"

    # Trailing backend
    args2 = parser.parse_args(["db", "status", "--backend", "postgres"])
    assert getattr(args2, "backend", None) == "postgres"


def test_format_minutes() -> None:
    assert _format_minutes(0) == "0m"
    assert _format_minutes(-5) == "0m"
    assert _format_minutes(45) == "45m"
    assert _format_minutes(60) == "1h 0m"
    assert _format_minutes(135) == "2h 15m"


def test_parse_datetime_valid() -> None:
    dt = _parse_datetime("2026-09-03 08:30:00")
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 3
    assert dt.hour == 8
    assert dt.minute == 30


def test_parse_datetime_invalid() -> None:
    with pytest.raises(Exception):
        _parse_datetime("fecha_invalida")

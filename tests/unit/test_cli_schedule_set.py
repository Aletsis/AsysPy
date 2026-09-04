"""Pruebas unitarias para el comando asistpy schedule set."""

from datetime import time
from unittest.mock import patch

from attendance.adapters.cli.main import main
from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.enums import AssignmentMode, RotationFrequency
from attendance.domain.schedule.shift import ShiftDefinition


def _setup_test_bundle():
    bundle = PersistenceFactory.create_bundle(backend="memory")
    emp = Employee(
        id=None,
        pin="E100",
        first_name="Carlos",
        paternal_last_name="Gomez",
        sex=Sex.MALE,
    )
    bundle.employee_repo.save(emp)

    s1 = ShiftDefinition(
        id=None,
        name="Matutino 08:00 - 16:00",
        start_time=time(8, 0),
        end_time=time(16, 0),
        tolerance_minutes=15,
    )
    s2 = ShiftDefinition(
        id=None,
        name="Vespertino 14:00 - 22:00",
        start_time=time(14, 0),
        end_time=time(22, 0),
        tolerance_minutes=15,
    )
    bundle.shift_repo.save(s1)
    bundle.shift_repo.save(s2)
    return bundle


def test_cli_schedule_set_fixed_shift_and_rest(capsys) -> None:
    """Verifica asistpy schedule set para turno fijo y descanso fijo."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
            "--shift-id",
            "1",
            "--rest-days",
            "domingo",
            "--valid-from",
            "2026-03-02",
            "--preview-days",
            "14",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Proyección de Rol de Turnos" in out
        assert "DESCANSO" in out
        assert "LABORABLE" in out
        assert "Horario y descansos establecidos exitosamente" in out

        # Verificar en repositorio
        assigns = [a for a in bundle.schedule_assignment_repo.list_all() if a.employee_pin == "E100"]
        assert len(assigns) == 1
        assert assigns[0].mode == AssignmentMode.FIXED
        assert assigns[0].shift_definition_id == 1
        assert assigns[0].rotation_pattern_id is None


def test_cli_schedule_set_rolling_rest(capsys) -> None:
    """Verifica asistpy schedule set con descanso que se recorre al siguiente día."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
            "--shift-id",
            "1",
            "--rolling-rest",
            "--rolling-start",
            "domingo",
            "--rolling-interval",
            "1",
            "--valid-from",
            "2026-03-02",
            "--preview-days",
            "21",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Patrón generado: Rol Carlos Gomez (Descanso Rolado" in out
        assert "Modo: ROTATING" in out

        patterns = bundle.rotation_pattern_repo.list_all()
        assert len(patterns) == 1
        assert patterns[0].frequency == RotationFrequency.DAILY
        assert len(patterns[0].shift_sequence) == 49


def test_cli_schedule_set_rotating_shifts(capsys) -> None:
    """Verifica asistpy schedule set con turnos rotativos semanales."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
            "--rotating-shifts",
            "1,2",
            "--shift-freq",
            "weekly",
            "--rest-days",
            "domingo",
            "--valid-from",
            "2026-03-02",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Patrón generado" in out

        patterns = bundle.rotation_pattern_repo.list_all()
        assert len(patterns) == 1
        assert len(patterns[0].shift_sequence) == 14


def test_cli_schedule_set_cycle_rest(capsys) -> None:
    """Verifica asistpy schedule set con ciclo continuo 6x1."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
            "--shift-id",
            "1",
            "--cycle-rest",
            "6x1",
            "--valid-from",
            "2026-03-02",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "(6x1)" in out

        patterns = bundle.rotation_pattern_repo.list_all()
        assert len(patterns) == 1
        assert len(patterns[0].shift_sequence) == 7
        assert patterns[0].shift_sequence == [1, 1, 1, 1, 1, 1, None]


def test_cli_schedule_set_preview_only(capsys) -> None:
    """Verifica que con --preview-only se muestre la tabla sin guardar en BD."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
            "--shift-id",
            "1",
            "--rolling-rest",
            "--preview-only",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Proyección de Rol de Turnos" in out
        assert "Modo de solo previsualización. No se realizaron cambios" in out

        # Verificar que NO se persistió nada
        assert len(bundle.schedule_assignment_repo.list_all()) == 0
        assert len(bundle.rotation_pattern_repo.list_all()) == 0


def test_cli_schedule_set_validation_errors(capsys) -> None:
    """Verifica mensajes de error ante parámetros inválidos."""
    bundle = _setup_test_bundle()
    with patch("attendance.adapters.cli.context.CLIContext.get_bundle", return_value=bundle):
        # Empleado inexistente
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "NO_EXISTE",
            "--shift-id",
            "1",
        ])
        assert code == 1
        err = capsys.readouterr().err
        assert "Empleado con PIN 'NO_EXISTE' no encontrado" in err

        # Falta shift-id y rotating-shifts
        code = main([
            "schedule",
            "set",
            "--employee-pin",
            "E100",
        ])
        assert code == 1
        err = capsys.readouterr().err
        assert "Debe especificar --shift-id" in err

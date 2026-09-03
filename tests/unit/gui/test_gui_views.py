"""Pruebas unitarias para vistas y tema de la GUI."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from attendance.adapters.gui.config import ConfigManager
from attendance.adapters.gui.main_window import MainWindow
from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.views import (
    AttendanceView,
    DashboardView,
    DevicesView,
    EmployeesView,
    EvaluationView,
    SchedulesView,
    SettingsView,
    SetupWizardDialog,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Fixture de QApplication en modo offscreen para pruebas en entornos headless."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_app_state(tmp_path: Path) -> AppState:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    cm.save(backend="memory", database_url="memory://", first_run_completed=True)
    return AppState(config_manager=cm)


def test_theme_contains_user_palette() -> None:
    stylesheet = Theme.get_stylesheet()
    # Paleta solicitada por el usuario
    assert "#09091A" in stylesheet
    assert "#FFFFFF" in stylesheet
    assert "#276EF1" in stylesheet
    assert "#6B6B6B" in stylesheet


def test_setup_wizard_dialog_instantiation(qapp: QApplication, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    wizard = SetupWizardDialog(config_manager=cm)
    assert wizard is not None
    assert wizard.windowTitle() == "AsistPy - Asistente de Configuración Inicial"


def test_views_instantiation(qapp: QApplication, mock_app_state: AppState) -> None:
    dash = DashboardView(mock_app_state)
    assert dash is not None

    devs = DevicesView(mock_app_state)
    assert devs is not None

    emps = EmployeesView(mock_app_state)
    assert emps is not None

    sched = SchedulesView(mock_app_state)
    assert sched is not None

    att = AttendanceView(mock_app_state)
    assert att is not None

    eval_v = EvaluationView(mock_app_state)
    assert eval_v is not None

    sett = SettingsView(mock_app_state)
    assert sett is not None


def test_main_window_navigation(qapp: QApplication, mock_app_state: AppState) -> None:
    win = MainWindow(mock_app_state)
    assert win is not None
    assert win.stack.count() == 7
    # Cambiar de vista a dispositivos (índice 1)
    win._on_nav_clicked(1)
    assert win.stack.currentIndex() == 1

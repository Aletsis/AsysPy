"""Pruebas unitarias para el estado reactivo de la GUI."""

from pathlib import Path

from attendance.adapters.gui.config import ConfigManager
from attendance.adapters.gui.state import AppState


def test_app_state_initialization(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    cm.save(backend="memory", database_url="memory://", first_run_completed=True)

    state = AppState(config_manager=cm)
    assert state.bundle is not None
    assert state.config.backend == "memory"


def test_app_state_signals(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    cm.save(backend="memory", database_url="memory://", first_run_completed=True)

    state = AppState(config_manager=cm)

    received_notifications: list[tuple[str, str]] = []
    state.notification_requested.connect(lambda lvl, msg: received_notifications.append((lvl, msg)))

    state.notify("Mensaje de prueba", "success")
    assert len(received_notifications) == 1
    assert received_notifications[0] == ("success", "Mensaje de prueba")

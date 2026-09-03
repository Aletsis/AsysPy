"""Pruebas unitarias para la configuración y persistencia de escritorio."""

from pathlib import Path

from attendance.adapters.gui.config import ConfigManager


def test_is_first_run_when_env_file_missing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    manager = ConfigManager(env_path=env_file)
    assert manager.is_first_run() is True


def test_save_and_load_config(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    manager = ConfigManager(env_path=env_file)

    manager.save(
        backend="postgres",
        database_url="postgresql+psycopg://postgres:pass@localhost:5432/asistpy",
        first_run_completed=True,
        theme="dark",
    )

    assert env_file.exists()
    config = manager.load()
    assert config.backend == "postgres"
    assert "postgresql+psycopg" in config.database_url
    assert config.first_run_completed is True
    assert config.theme == "dark"
    assert config.is_sqlite is False


def test_sqlite_detection(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    manager = ConfigManager(env_path=env_file)
    manager.save(
        backend="sqlite",
        database_url="sqlite:///test.db",
        first_run_completed=True,
    )
    config = manager.load()
    assert config.is_sqlite is True

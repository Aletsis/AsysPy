"""Estado global y contenedor de servicios para la GUI de AsistPy."""

import logging

from PySide6.QtCore import QObject, Signal

from attendance.adapters.gui.config import ConfigManager, DesktopConfig
from attendance.adapters.persistence.factory import PersistenceBundle, PersistenceFactory

logger = logging.getLogger(__name__)


class AppState(QObject):
    """Mantiene el estado en memoria y notifica cambios a la UI mediante señales Qt."""

    # Señales reactivas
    database_changed = Signal(str)            # Emite el nombre del backend
    data_updated = Signal(str)                # Emite el tipo de entidad actualizada (ej. 'devices', 'attendance')
    notification_requested = Signal(str, str) # Emite (tipo, mensaje): tipo='info'|'success'|'warning'|'error'

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.config: DesktopConfig = self.config_manager.load()
        self.bundle: PersistenceBundle | None = None
        self._init_bundle()

    def _init_bundle(self) -> None:
        """Inicializa o actualiza el PersistenceBundle según la configuración actual."""
        try:
            self.bundle = PersistenceFactory.create_bundle(
                backend=self.config.backend,
                connection_string=self.config.database_url,
                init_tables=False,
            )
        except Exception as e:
            logger.warning(f"No se pudo inicializar la persistencia inicial: {e}")
            self.bundle = None

    def reload_persistence(self, backend: str, database_url: str, init_tables: bool = True) -> PersistenceBundle:
        """Reconfigura la persistencia activa tras un cambio de configuración o asistente."""
        new_bundle = PersistenceFactory.create_bundle(
            backend=backend,
            connection_string=database_url,
            init_tables=init_tables,
        )
        self.bundle = new_bundle
        self.config.backend = backend
        self.config.database_url = database_url
        self.config.first_run_completed = True
        self.config_manager.save(
            backend=backend,
            database_url=database_url,
            first_run_completed=True,
            theme=self.config.theme,
        )
        self.database_changed.emit(backend)
        self.data_updated.emit("all")
        return new_bundle

    def notify(self, message: str, level: str = "info") -> None:
        """Dispara una notificación a la barra de estado o toast."""
        self.notification_requested.emit(level, message)

"""Punto de inicio y ciclo de vida de la aplicación de escritorio AsistPy GUI."""

import sys

from PySide6.QtWidgets import QApplication, QDialog

from attendance.adapters.gui.config import ConfigManager
from attendance.adapters.gui.main_window import MainWindow
from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.views.wizard_view import SetupWizardDialog


def run_app() -> int:
    """Arranca la aplicación de escritorio y gestiona el flujo de bienvenida si es primer uso."""
    app = QApplication(sys.argv)
    app.setApplicationName("AsistPy")
    app.setApplicationDisplayName("AsistPy - Control de Asistencia Biométrico")
    app.setOrganizationName("AsistPy")

    config_manager = ConfigManager()
    state = AppState(config_manager=config_manager)

    # Si es primer uso o falta configuración, lanzar Asistente Interactivo
    if config_manager.is_first_run():
        wizard = SetupWizardDialog(config_manager=config_manager)
        res = wizard.exec()
        if res != QDialog.DialogCode.Accepted:
            # El usuario canceló la configuración inicial
            return 0
        # Recargar estado con los nuevos valores del asistente
        conf = config_manager.load()
        state.reload_persistence(conf.backend, conf.database_url, init_tables=False)

    # Iniciar ventana principal
    window = MainWindow(app_state=state)
    window.show()

    return app.exec()

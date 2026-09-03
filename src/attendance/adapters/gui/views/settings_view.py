"""Vista de Configuración del Sistema y Entorno de Persistencia."""

import importlib.util

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.views.wizard_view import SetupWizardDialog


class SettingsView(QWidget):
    """Pantalla para consultar estado de drivers, base de datos y reconfiguración."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._setup_ui()
        self.refresh_settings()

        self.state.database_changed.connect(lambda _: self.refresh_settings())

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Encabezado
        title = QLabel("Configuración del Sistema")
        title.setObjectName("h1Title")
        sub = QLabel("Administración de persistencia, drivers instalados y parámetros de despliegue.")
        sub.setObjectName("mutedLabel")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Tarjeta de Base de Datos Activa
        db_card = QFrame()
        db_card.setObjectName("cardFrame")
        db_layout = QVBoxLayout(db_card)
        db_layout.setSpacing(10)

        db_title = QLabel("Persistencia y Conexión Activa")
        db_title.setObjectName("h2Title")
        db_layout.addWidget(db_title)

        self.lbl_backend = QLabel("Motor: -")
        self.lbl_db_url = QLabel("Cadena de Conexión: -")
        self.lbl_db_url.setObjectName("mutedLabel")
        db_layout.addWidget(self.lbl_backend)
        db_layout.addWidget(self.lbl_db_url)

        btn_row = QHBoxLayout()
        self.btn_run_wizard = QPushButton("⚙️ Volver a Ejecutar Asistente de Configuración")
        self.btn_run_wizard.setObjectName("primaryBtn")
        self.btn_run_wizard.clicked.connect(self._reopen_wizard)

        self.btn_reinit_tables = QPushButton("Inicializar / Reparar Tablas")
        self.btn_reinit_tables.clicked.connect(self._reinit_tables)

        btn_row.addWidget(self.btn_run_wizard)
        btn_row.addWidget(self.btn_reinit_tables)
        btn_row.addStretch()
        db_layout.addLayout(btn_row)

        layout.addWidget(db_card)

        # Tarjeta de Drivers Opcionales
        drivers_card = QFrame()
        drivers_card.setObjectName("cardFrame")
        dr_layout = QVBoxLayout(drivers_card)
        dr_layout.setSpacing(10)

        dr_title = QLabel("Diagnóstico de Drivers y Módulos Opcionales")
        dr_title.setObjectName("h2Title")
        dr_layout.addWidget(dr_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        drivers = [
            ("SQLite (Nativo)", "sqlite3", "Instalado por defecto en Python"),
            ("PostgreSQL (asistpy[postgres])", "psycopg", "Driver psycopg v3"),
            ("MySQL / MariaDB (asistpy[mysql])", "pymysql", "Driver PyMySQL"),
            ("SQL Server (asistpy[sqlserver])", "pyodbc", "Driver ODBC para SQL Server"),
            ("MongoDB (asistpy[mongo])", "pymongo", "Cliente NoSQL PyMongo"),
            ("Protocolo Biométrico ZKTeco", "zk", "Librería pyzk (TCP 4370)"),
        ]

        for row, (name, mod, desc) in enumerate(drivers):
            lbl_name = QLabel(name)
            installed = importlib.util.find_spec(mod) is not None
            lbl_status = QLabel("✓ DISPONIBLE" if installed else "✗ NO INSTALADO")
            lbl_status.setStyleSheet(
                f"color: {Theme.SUCCESS if installed else Theme.MUTED}; font-weight: bold;"
            )
            lbl_desc = QLabel(desc)
            lbl_desc.setObjectName("mutedLabel")

            grid.addWidget(lbl_name, row, 0)
            grid.addWidget(lbl_status, row, 1)
            grid.addWidget(lbl_desc, row, 2)

        dr_layout.addLayout(grid)
        layout.addWidget(drivers_card)

        # Info del Software
        about_card = QFrame()
        about_card.setObjectName("cardFrame")
        ab_layout = QVBoxLayout(about_card)
        ab_layout.setSpacing(6)

        ab_title = QLabel("Acerca de AsistPy")
        ab_title.setObjectName("h2Title")
        ab_layout.addWidget(ab_title)

        ab_desc = QLabel(
            "AsistPy v0.1.0 • Diseñado bajo Arquitectura Hexagonal y DDD.\n"
            "Despliegue modular: solo instala lo necesario en cada estación de trabajo."
        )
        ab_desc.setObjectName("mutedLabel")
        ab_layout.addWidget(ab_desc)

        layout.addWidget(about_card)
        layout.addStretch()

    def refresh_settings(self) -> None:
        self.lbl_backend.setText(f"Motor: {self.state.config.backend.upper()}")
        self.lbl_db_url.setText(f"Cadena de Conexión: {self.state.config.database_url}")

    def _reopen_wizard(self) -> None:
        wizard = SetupWizardDialog(config_manager=self.state.config_manager, parent=self)
        if wizard.exec() == SetupWizardDialog.DialogCode.Accepted:
            # Recargar estado
            conf = self.state.config_manager.load()
            self.state.reload_persistence(conf.backend, conf.database_url, init_tables=False)
            self.refresh_settings()
            self.state.notify("Configuración de entorno actualizada.", "success")

    def _reinit_tables(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirmar Inicialización",
            "¿Desea inicializar/actualizar la estructura de tablas de la base de datos?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                bundle = self.state.bundle
                if bundle and bundle.database:
                    bundle.database.init_tables()
                    self.state.notify("Estructura de tablas actualizada correctamente.", "success")
                else:
                    self.state.notify("La base de datos actual no requiere inicialización DDL.", "info")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudieron inicializar las tablas: {e}")

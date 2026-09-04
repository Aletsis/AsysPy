"""Vista de Tablero Principal (Dashboard) para AsistPy GUI."""

from datetime import date

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.workers.device_worker import DeviceSyncWorker


class MetricCard(QFrame):
    """Tarjeta visual moderna para métricas y KPIs."""

    def __init__(self, title: str, value: str = "0", subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("mutedLabel")
        layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {Theme.TEXT_MAIN};")
        layout.addWidget(self.lbl_value)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("mutedLabel")
        layout.addWidget(self.lbl_sub)

    def set_value(self, value: str) -> None:
        self.lbl_value.setText(value)


class DashboardView(QWidget):
    """Panel principal con métricas en tiempo real y accesos directos."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._sync_worker: DeviceSyncWorker | None = None
        self._setup_ui()
        self.refresh_data()

        # Conectar a señales reactivas del estado
        self.state.data_updated.connect(lambda _: self.refresh_data())

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Encabezado superior
        top_bar = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Tablero de Control")
        title.setObjectName("h1Title")
        sub = QLabel(f"Monitoreo general y estado del sistema • {date.today().strftime('%d/%m/%Y')}")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top_bar.addLayout(header)
        top_bar.addStretch()

        self.btn_sync_all = QPushButton("🔄 Sincronizar Todos los Relojes")
        self.btn_sync_all.setObjectName("primaryBtn")
        self.btn_sync_all.clicked.connect(self._sync_all_devices)
        top_bar.addWidget(self.btn_sync_all)

        main_layout.addLayout(top_bar)

        # Barra de Progreso para Sincronización
        self.progress_container = QWidget()
        self.progress_container.setVisible(False)
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_prog_status = QLabel("Sincronizando dispositivos...")
        self.lbl_prog_status.setObjectName("mutedLabel")
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)  # indeterminado
        self.prog_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {Theme.PRIMARY}; border-radius: 4px; }}")
        prog_layout.addWidget(self.lbl_prog_status)
        prog_layout.addWidget(self.prog_bar)
        main_layout.addWidget(self.progress_container)

        # Grid de Tarjetas de Métricas (2 filas x 3 columnas)
        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_devices = MetricCard("Relojes Biométricos", "0", "0 Activos")
        self.card_employees = MetricCard("Colaboradores Registrados", "0", "En plantilla")
        self.card_attendance = MetricCard("Marcaciones Hoy", "0", "Eventos sincronizados")
        self.card_branches = MetricCard("Sucursales", "0", "Ubicaciones operativas")
        self.card_departments = MetricCard("Departamentos", "0", "Áreas activas")
        self.card_positions = MetricCard("Puestos / Cargos", "0", "Catálogo laboral")

        grid.addWidget(self.card_devices, 0, 0)
        grid.addWidget(self.card_employees, 0, 1)
        grid.addWidget(self.card_attendance, 0, 2)
        grid.addWidget(self.card_branches, 1, 0)
        grid.addWidget(self.card_departments, 1, 1)
        grid.addWidget(self.card_positions, 1, 2)
        main_layout.addLayout(grid)

        # Panel de Estado Rápido y Consejos
        info_frame = QFrame()
        info_frame.setObjectName("cardFrame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)

        info_title = QLabel("Estado del Entorno y Persistencia")
        info_title.setObjectName("h2Title")
        info_layout.addWidget(info_title)

        self.lbl_backend_info = QLabel(f"Motor de Persistencia Activo: {self.state.config.backend.upper()}")
        info_layout.addWidget(self.lbl_backend_info)

        self.lbl_db_info = QLabel(f"Cadena de Conexión: {self.state.config.database_url}")
        self.lbl_db_info.setObjectName("mutedLabel")
        info_layout.addWidget(self.lbl_db_info)

        main_layout.addWidget(info_frame)
        main_layout.addStretch()

    def refresh_data(self) -> None:
        """Actualiza los contadores consultando los repositorios del PersistenceBundle."""
        bundle = self.state.bundle
        if not bundle:
            return

        try:
            devices = bundle.device_repo.list_all()
            active_devices = sum(1 for d in devices if d.active)
            self.card_devices.set_value(str(len(devices)))
            self.card_devices.lbl_sub.setText(f"{active_devices} Activos")

            employees = bundle.employee_repo.list_all()
            active_employees = sum(1 for e in employees if e.active)
            self.card_employees.set_value(str(len(employees)))
            self.card_employees.lbl_sub.setText(f"{active_employees} Activos en plantilla")

            branches = bundle.branch_repo.list_all()
            self.card_branches.set_value(str(len(branches)))

            depts = bundle.department_repo.list_all()
            self.card_departments.set_value(str(len(depts)))

            positions = bundle.position_repo.list_all() if bundle.position_repo else []
            self.card_positions.set_value(str(len(positions)))

            # Contar marcaciones de hoy
            today = date.today()
            raw_all = bundle.attendance_repo.list_all()
            raw_today = [log for log in raw_all if log.timestamp and log.timestamp.date() == today]
            self.card_attendance.set_value(str(len(raw_today)))

            self.lbl_backend_info.setText(f"Motor de Persistencia Activo: {self.state.config.backend.upper()}")
            self.lbl_db_info.setText(f"Cadena de Conexión: {self.state.config.database_url}")
        except Exception:
            pass

    def _sync_all_devices(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            self.state.notify("No hay conexión a base de datos configurada.", "error")
            return

        self.btn_sync_all.setEnabled(False)
        self.progress_container.setVisible(True)
        self.lbl_prog_status.setText("Iniciando sincronización masiva con relojes biométricos...")

        self._sync_worker = DeviceSyncWorker(bundle=bundle)
        self._sync_worker.finished_sync.connect(self._on_sync_finished)
        self._sync_worker.error_occurred.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self, success: bool, message: str, total_logs: int) -> None:
        self.btn_sync_all.setEnabled(True)
        self.progress_container.setVisible(False)
        level = "success" if success else "warning"
        self.state.notify(message, level)
        self.refresh_data()
        self.state.data_updated.emit("attendance")

    def _on_sync_error(self, err: str) -> None:
        self.btn_sync_all.setEnabled(True)
        self.progress_container.setVisible(False)
        self.state.notify(f"Error de sincronización: {err}", "error")

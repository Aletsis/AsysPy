"""Ventana principal (MainWindow) y marco de navegación para AsistPy GUI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

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
)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación de escritorio de AsistPy."""

    def __init__(self, app_state: AppState) -> None:
        super().__init__()
        self.state = app_state
        self.setWindowTitle("AsistPy - Control de Asistencia Biométrico")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barra Lateral de Navegación (Sidebar)
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(
            f"background-color: {Theme.BG_MAIN}; border-right: 1px solid {Theme.BORDER};"
        )
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(14, 18, 14, 18)
        s_layout.setSpacing(8)

        # Logo / Marca
        brand_layout = QHBoxLayout()
        lbl_logo = QLabel("🕒")
        lbl_logo.setStyleSheet("font-size: 24px;")
        lbl_brand = QLabel("AsistPy")
        lbl_brand.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {Theme.TEXT_MAIN}; letter-spacing: 0.5px;"
        )
        brand_layout.addWidget(lbl_logo)
        brand_layout.addWidget(lbl_brand)
        brand_layout.addStretch()
        s_layout.addLayout(brand_layout)

        lbl_sub = QLabel("Control Biométrico")
        lbl_sub.setObjectName("mutedLabel")
        lbl_sub.setStyleSheet("margin-bottom: 12px;")
        s_layout.addWidget(lbl_sub)

        # Botones de navegación
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.nav_buttons = [
            ("📊  Tablero Principal", 0),
            ("📡  Relojes Biométricos", 1),
            ("👥  Personal y Áreas", 2),
            ("📅  Turnos y Horarios", 3),
            ("📋  Marcaciones", 4),
            ("⚖️  Cierre y Evaluación", 5),
            ("⚙️  Configuración", 6),
        ]

        for text, index in self.nav_buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 10px 14px;
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                    color: {Theme.TEXT_MUTED};
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {Theme.BG_CARD_HOVER};
                    color: {Theme.TEXT_MAIN};
                }}
                QPushButton:checked {{
                    background-color: {Theme.PRIMARY};
                    color: #FFFFFF;
                    font-weight: 600;
                }}
            """)
            self.btn_group.addButton(btn, index)
            s_layout.addWidget(btn)

        s_layout.addStretch()

        # Indicador de persistencia en pie de sidebar
        self.lbl_sidebar_db = QLabel(f"BD: {self.state.config.backend.upper()}")
        self.lbl_sidebar_db.setObjectName("badgeWarning")
        self.lbl_sidebar_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s_layout.addWidget(self.lbl_sidebar_db)

        main_layout.addWidget(sidebar)

        # 2. Contenedor de Vistas (QStackedWidget)
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView(self.state)
        self.view_devices = DevicesView(self.state)
        self.view_employees = EmployeesView(self.state)
        self.view_schedules = SchedulesView(self.state)
        self.view_attendance = AttendanceView(self.state)
        self.view_evaluation = EvaluationView(self.state)
        self.view_settings = SettingsView(self.state)

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_devices)
        self.stack.addWidget(self.view_employees)
        self.stack.addWidget(self.view_schedules)
        self.stack.addWidget(self.view_attendance)
        self.stack.addWidget(self.view_evaluation)
        self.stack.addWidget(self.view_settings)

        main_layout.addWidget(self.stack)

        # 3. Barra de Estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("AsistPy listo.")

        # Seleccionar primera pestaña
        first_btn = self.btn_group.button(0)
        if first_btn:
            first_btn.setChecked(True)
        self.btn_group.idClicked.connect(self._on_nav_clicked)

    def _on_nav_clicked(self, view_id: int) -> None:
        self.stack.setCurrentIndex(view_id)

    def _connect_signals(self) -> None:
        self.state.notification_requested.connect(self._show_notification)
        self.state.database_changed.connect(self._on_database_changed)

    def _show_notification(self, level: str, message: str) -> None:
        prefix = {
            "success": "✓ ",
            "warning": "⚠️ ",
            "error": "✗ ",
            "info": "ℹ️ ",
        }.get(level, "")
        self.status_bar.showMessage(f"{prefix}{message}", 6000)

    def _on_database_changed(self, backend: str) -> None:
        self.lbl_sidebar_db.setText(f"BD: {backend.upper()}")

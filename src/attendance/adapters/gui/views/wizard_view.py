"""Asistente de configuración inicial (Setup Wizard) para AsistPy Desktop GUI.

Guía al usuario paso a paso en:
1. Selección de motor de base de datos (SQLite, PostgreSQL, MySQL, SQL Server).
2. Configuración y prueba de conexión.
3. Inicialización de tablas y catálogo base.
4. Registro y prueba del primer reloj biométrico ZKTeco.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.config import ConfigManager
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.workers.device_worker import DeviceProbeWorker
from attendance.adapters.persistence.factory import PersistenceFactory, check_driver_installed
from attendance.adapters.persistence.sql.database import Database
from attendance.domain.device.device import Device
from attendance.domain.organization.branch import Branch


class SetupWizardDialog(QDialog):
    """Diálogo interactivo para configuración en el primer arranque."""

    wizard_completed = Signal()

    def __init__(self, config_manager: ConfigManager | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager or ConfigManager()
        self.setWindowTitle("AsistPy - Asistente de Configuración Inicial")
        self.setMinimumSize(620, 500)
        self.setStyleSheet(Theme.get_stylesheet())

        self.tested_db_url: str | None = None
        self.tables_initialized = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado del Asistente
        header_layout = QVBoxLayout()
        self.title_label = QLabel("Bienvenido a AsistPy")
        self.title_label.setObjectName("h1Title")
        self.subtitle_label = QLabel("Configuremos el entorno según las necesidades de su despliegue.")
        self.subtitle_label.setObjectName("mutedLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        main_layout.addLayout(header_layout)

        # Barra de Pasos (Indicador superior)
        self.step_indicator = QLabel("Paso 1 de 4: Selección del Motor de Base de Datos")
        self.step_indicator.setObjectName("badgeWarning")
        main_layout.addWidget(self.step_indicator)

        # Contenedor de Pasos (QStackedWidget)
        self.stack = QStackedWidget()
        self._create_step1()
        self._create_step2()
        self._create_step3()
        self._create_step4()
        main_layout.addWidget(self.stack)

        # Botones de Navegación Inferiores
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("← Anterior")
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton("Siguiente →")
        self.btn_next.setObjectName("primaryBtn")
        self.btn_next.clicked.connect(self._on_next)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        main_layout.addLayout(nav_layout)

    # ================= PASO 1: SELECCIÓN DE MOTOR =================
    def _create_step1(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        info = QLabel(
            "Seleccione el motor de almacenamiento. Puede optar por una base local "
            "ligera o conectarse a un servidor corporativo existente:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.combo_engine = QComboBox()
        self.combo_engine.addItem("SQLite (Recomendado para puesto individual / caseta)", "sqlite")
        self.combo_engine.addItem("PostgreSQL (Servidor corporativo / central)", "postgres")
        self.combo_engine.addItem("MySQL / MariaDB", "mysql")
        self.combo_engine.addItem("Microsoft SQL Server", "sqlserver")
        self.combo_engine.currentIndexChanged.connect(self._on_engine_selected)

        form.addRow("Motor de Datos:", self.combo_engine)
        layout.addLayout(form)

        self.engine_desc = QLabel(
            "SQLite no requiere instalación externa ni servicios en segundo plano. "
            "Los datos se guardan en un archivo local en su computadora."
        )
        self.engine_desc.setObjectName("mutedLabel")
        self.engine_desc.setWordWrap(True)
        layout.addWidget(self.engine_desc)
        layout.addStretch()

        self.stack.addWidget(page)

    def _on_engine_selected(self) -> None:
        engine = self.combo_engine.currentData()
        if engine == "sqlite":
            self.engine_desc.setText(
                "SQLite: Almacenamiento local directo. No requiere configuración de red ni servidores."
            )
            self.txt_db_host.setText("localhost")
            self.txt_db_port.setText("")
            self.txt_db_name.setText("asistpy.db")
            self.txt_db_user.setText("")
            self.txt_db_pass.setText("")
            self.sqlite_container.setVisible(True)
            self.remote_db_container.setVisible(False)
        else:
            self.sqlite_container.setVisible(False)
            self.remote_db_container.setVisible(True)
            if engine == "postgres":
                self.engine_desc.setText("PostgreSQL: Requiere el paquete opcional 'asistpy[postgres]'.")
                self.txt_db_port.setText("5432")
                self.txt_db_name.setText("asistpy")
                self.txt_db_user.setText("postgres")
            elif engine == "mysql":
                self.engine_desc.setText("MySQL: Requiere el paquete opcional 'asistpy[mysql]'.")
                self.txt_db_port.setText("3306")
                self.txt_db_name.setText("asistpy")
                self.txt_db_user.setText("root")
            elif engine == "sqlserver":
                self.engine_desc.setText("SQL Server: Requiere el paquete opcional 'asistpy[sqlserver]'.")
                self.txt_db_port.setText("1433")
                self.txt_db_name.setText("asistpy")
                self.txt_db_user.setText("sa")

    # ================= PASO 2: PARÁMETROS DE CONEXIÓN =================
    def _create_step2(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        # Contenedor SQLite
        self.sqlite_container = QWidget()
        sq_layout = QFormLayout(self.sqlite_container)
        self.txt_sqlite_file = QLineEdit("asistpy.db")
        sq_layout.addRow("Nombre/Ruta del archivo SQLite:", self.txt_sqlite_file)
        layout.addWidget(self.sqlite_container)

        # Contenedor BD Remota
        self.remote_db_container = QWidget()
        self.remote_db_container.setVisible(False)
        rm_layout = QFormLayout(self.remote_db_container)
        self.txt_db_host = QLineEdit("localhost")
        self.txt_db_port = QLineEdit("5432")
        self.txt_db_name = QLineEdit("asistpy")
        self.txt_db_user = QLineEdit("postgres")
        self.txt_db_pass = QLineEdit()
        self.txt_db_pass.setEchoMode(QLineEdit.EchoMode.Password)

        rm_layout.addRow("Host / Dirección IP:", self.txt_db_host)
        rm_layout.addRow("Puerto de Red:", self.txt_db_port)
        rm_layout.addRow("Nombre de Base de Datos:", self.txt_db_name)
        rm_layout.addRow("Usuario:", self.txt_db_user)
        rm_layout.addRow("Contraseña:", self.txt_db_pass)
        layout.addWidget(self.remote_db_container)

        # Botón Probar Conexión
        self.btn_test_db = QPushButton("⚡ Probar Conexión")
        self.btn_test_db.clicked.connect(self._test_db_connection)
        layout.addWidget(self.btn_test_db)

        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        layout.addWidget(self.lbl_test_result)
        layout.addStretch()

        self.stack.addWidget(page)

    def _build_connection_string(self) -> tuple[str, str]:
        engine = self.combo_engine.currentData()
        if engine == "sqlite":
            path = self.txt_sqlite_file.text().strip() or "asistpy.db"
            return "sqlite", f"sqlite:///{path}"
        else:
            host = self.txt_db_host.text().strip() or "localhost"
            port = self.txt_db_port.text().strip()
            name = self.txt_db_name.text().strip() or "asistpy"
            user = self.txt_db_user.text().strip()
            password = self.txt_db_pass.text().strip()
            auth = f"{user}:{password}@" if user else ""
            port_part = f":{port}" if port else ""

            if engine == "postgres":
                url = f"postgresql+psycopg://{auth}{host}{port_part}/{name}"
            elif engine == "mysql":
                url = f"mysql+pymysql://{auth}{host}{port_part}/{name}"
            elif engine == "sqlserver":
                url = f"mssql+pyodbc://{auth}{host}{port_part}/{name}?driver=ODBC+Driver+17+for+SQL+Server"
            else:
                url = "sqlite:///asistpy.db"
            return engine, url

    def _test_db_connection(self) -> None:
        engine, url = self._build_connection_string()
        self.lbl_test_result.setText("Probando conexión...")
        self.lbl_test_result.setStyleSheet("color: #276EF1;")

        # Validar si el driver opcional está presente
        try:
            if engine == "postgres":
                check_driver_installed("psycopg", "postgres", "PostgreSQL")
            elif engine == "mysql":
                check_driver_installed("pymysql", "mysql", "MySQL")
            elif engine == "sqlserver":
                check_driver_installed("pyodbc", "sqlserver", "SQL Server")

            db = Database(url)
            # Prueba de ping al motor
            with db.engine.connect():
                pass

            self.tested_db_url = url
            self.lbl_test_result.setText("✓ Conexión establecida exitosamente con el motor de base de datos.")
            self.lbl_test_result.setStyleSheet("color: #10B981; font-weight: bold;")
        except Exception as e:
            self.tested_db_url = None
            self.lbl_test_result.setText(f"✗ Falló la conexión: {e}")
            self.lbl_test_result.setStyleSheet("color: #EF4444; font-weight: bold;")

    # ================= PASO 3: INICIALIZACIÓN DE TABLAS =================
    def _create_step3(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        info = QLabel(
            "Se crearán automáticamente las tablas del sistema (empleados, relojes, "
            "turnos, asistencias y auditoría) y se registrará la sucursal principal inicial."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.txt_initial_branch = QLineEdit("Oficina Matriz")
        form.addRow("Nombre de Sucursal Inicial:", self.txt_initial_branch)
        layout.addLayout(form)

        self.btn_init_tables = QPushButton("⚙️ Inicializar Tablas y Catálogos")
        self.btn_init_tables.setObjectName("primaryBtn")
        self.btn_init_tables.clicked.connect(self._init_tables_action)
        layout.addWidget(self.btn_init_tables)

        self.lbl_init_status = QLabel("")
        self.lbl_init_status.setWordWrap(True)
        layout.addWidget(self.lbl_init_status)
        layout.addStretch()

        self.stack.addWidget(page)

    def _init_tables_action(self) -> None:
        engine, url = self._build_connection_string()
        try:
            db = Database(url)
            db.init_tables()
            bundle = PersistenceFactory.create_sql_bundle_from_session_factory(db.session_factory)

            # Crear sucursal inicial si no existe
            branch_name = self.txt_initial_branch.text().strip() or "Oficina Matriz"
            existing = bundle.branch_repo.get_by_code("MATRIZ")
            if not existing:
                b = Branch(id=None, name=branch_name, code="MATRIZ", timezone="America/Mexico_City")
                bundle.branch_repo.save(b)

            self.tables_initialized = True
            self.lbl_init_status.setText(f"✓ Tablas creadas correctamente. Sucursal '{branch_name}' registrada.")
            self.lbl_init_status.setStyleSheet("color: #10B981; font-weight: bold;")
        except Exception as e:
            self.tables_initialized = False
            self.lbl_init_status.setText(f"✗ Error al inicializar tablas: {e}")
            self.lbl_init_status.setStyleSheet("color: #EF4444; font-weight: bold;")

    # ================= PASO 4: PRIMER RELOJ BIOMÉTRICO =================
    def _create_step4(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        info = QLabel(
            "Opcional: Registre los datos de su primer reloj biométrico ZKTeco. "
            "Podrá agregar más dispositivos en cualquier momento desde la pantalla principal."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.txt_dev_name = QLineEdit("Reloj Principal")
        self.txt_dev_ip = QLineEdit("192.168.1.201")
        self.txt_dev_port = QLineEdit("4370")
        form.addRow("Nombre del Dispositivo:", self.txt_dev_name)
        form.addRow("Dirección IP:", self.txt_dev_ip)
        form.addRow("Puerto TCP (ZK):", self.txt_dev_port)
        layout.addLayout(form)

        test_row = QHBoxLayout()
        self.btn_test_device = QPushButton("📡 Probar Conectividad con Reloj")
        self.btn_test_device.clicked.connect(self._probe_device)
        test_row.addWidget(self.btn_test_device)
        layout.addLayout(test_row)

        self.lbl_device_result = QLabel("")
        self.lbl_device_result.setWordWrap(True)
        layout.addWidget(self.lbl_device_result)
        layout.addStretch()

        self.stack.addWidget(page)

    def _probe_device(self) -> None:
        ip = self.txt_dev_ip.text().strip()
        port = int(self.txt_dev_port.text().strip() or "4370")
        self.btn_test_device.setEnabled(False)
        self.lbl_device_result.setText("Verificando conexión con el reloj biométrico...")
        self.lbl_device_result.setStyleSheet("color: #276EF1;")

        self._probe_worker = DeviceProbeWorker(ip=ip, port=port)
        self._probe_worker.finished_probe.connect(self._on_probe_device_finished)
        self._probe_worker.start()

    def _on_probe_device_finished(self, success: bool, message: str, info: dict) -> None:
        self.btn_test_device.setEnabled(True)
        if success:
            firmware = info.get("firmware", "")
            fw_text = f" (Firmware: {firmware})" if firmware else ""
            self.lbl_device_result.setText(f"✓ {message}{fw_text}")
            self.lbl_device_result.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.lbl_device_result.setText(f"✗ {message}")
            self.lbl_device_result.setStyleSheet("color: #EF4444;")

    # ================= NAVEGACIÓN Y FINALIZACIÓN =================
    def _update_indicators(self, index: int) -> None:
        titles = [
            "Paso 1 de 4: Selección del Motor de Base de Datos",
            "Paso 2 de 4: Configuración de Parámetros de Conexión",
            "Paso 3 de 4: Inicialización de Tablas",
            "Paso 4 de 4: Configuración del Primer Reloj Biométrico",
        ]
        self.step_indicator.setText(titles[index])
        self.btn_prev.setEnabled(index > 0)
        self.btn_next.setText("Completar y Arrancar" if index == 3 else "Siguiente →")

    def _on_prev(self) -> None:
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self._update_indicators(curr - 1)

    def _on_next(self) -> None:
        curr = self.stack.currentIndex()
        if curr == 0:
            self.stack.setCurrentIndex(1)
            self._update_indicators(1)
        elif curr == 1:
            # Validar que al menos se haya ingresado URL o se prueba automáticamente
            engine, url = self._build_connection_string()
            if not self.tested_db_url:
                # Probar automáticamente si no se ha presionado el botón
                self._test_db_connection()
                if not self.tested_db_url:
                    confirm = QMessageBox.question(
                        self,
                        "Advertencia de Conexión",
                        "La conexión con la base de datos no fue verificada exitosamente. ¿Desea continuar de todos modos?",
                    )
                    if confirm != QMessageBox.StandardButton.Yes:
                        return
            self.stack.setCurrentIndex(2)
            self._update_indicators(2)
        elif curr == 2:
            if not self.tables_initialized:
                # Intentar inicializar automáticamente
                self._init_tables_action()
                if not self.tables_initialized:
                    QMessageBox.warning(
                        self,
                        "Tablas requeridas",
                        "Debe inicializar las tablas antes de continuar con la configuración del sistema.",
                    )
                    return
            self.stack.setCurrentIndex(3)
            self._update_indicators(3)
        elif curr == 3:
            # Guardar configuración y cerrar
            self._finish_wizard()

    def _finish_wizard(self) -> None:
        engine, url = self._build_connection_string()
        self.config_manager.save(
            backend=engine,
            database_url=url,
            first_run_completed=True,
            theme="dark",
        )

        # Si se completó el formulario del reloj, registrarlo
        dev_name = self.txt_dev_name.text().strip()
        dev_ip = self.txt_dev_ip.text().strip()
        dev_port = int(self.txt_dev_port.text().strip() or "4370")
        if dev_name and dev_ip:
            try:
                bundle = PersistenceFactory.create_bundle(backend=engine, connection_string=url)
                branches = bundle.branch_repo.list_all()
                branch_id = branches[0].id if branches and branches[0].id is not None else 0
                dev = Device(
                    id=None,
                    name=dev_name,
                    ip_address=dev_ip,
                    port=dev_port,
                    branch_id=branch_id,
                    active=True,
                )
                bundle.device_repo.save(dev)
            except Exception:
                pass

        self.wizard_completed.emit()
        self.accept()

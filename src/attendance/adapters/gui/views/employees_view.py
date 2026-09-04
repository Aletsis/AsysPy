"""Vista de Gestión de Personal y Organización (Empleados, Puestos, Departamentos, Sucursales)."""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.views.schedule_dialog import SetEmployeeScheduleDialog
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.address import Address
from attendance.domain.organization.branch import Branch
from attendance.domain.organization.department import Department
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.organization.position import Position

# ============================================================================
# DIÁLOGOS DE COLABORADORES
# ============================================================================


class EmployeeDetailDialog(QDialog):
    """Ficha técnica detallada de un colaborador con todos sus atributos."""

    def __init__(
        self, app_state: AppState, employee: Employee, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.employee = employee
        self.setWindowTitle(f"Ficha de Colaborador: {employee.full_name} ({employee.pin})")
        self.setMinimumWidth(560)
        self.setStyleSheet(Theme.get_stylesheet())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        bundle = self.state.bundle
        dept_name = "N/A"
        branch_name = "N/A"
        pos_name = "Sin puesto"
        if bundle:
            dept = bundle.department_repo.get_by_id(self.employee.department_id)
            if dept:
                dept_name = f"{dept.name} (#{dept.id})"
            branch = bundle.branch_repo.get_by_id(self.employee.home_branch_id)
            if branch:
                branch_name = f"{branch.name} (#{branch.id})"
            if self.employee.position_id and bundle.position_repo:
                pos = bundle.position_repo.get_by_id(self.employee.position_id)
                if pos:
                    pos_name = f"{pos.name} (#{pos.id})"

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        pwd_display = "******** (Configurada)" if self.employee.password else "No establecida"
        fp_display = (
            f"{len(self.employee.fingerprints)} registrada(s)"
            if self.employee.fingerprints
            else "0 registradas"
        )

        rows = [
            ("ID Interno", str(self.employee.id or "-")),
            ("PIN / ID Biométrico", self.employee.pin),
            ("Nombre Completo", self.employee.full_name),
            ("Nombres", self.employee.first_name),
            ("Apellido Paterno", self.employee.paternal_last_name),
            ("Apellido Materno", self.employee.maternal_last_name or "-"),
            ("Sexo", "Masculino" if self.employee.sex == Sex.MALE else "Femenino"),
            ("Fecha de Ingreso", self.employee.hire_date.isoformat()),
            ("Puesto / Cargo", pos_name),
            ("Departamento", dept_name),
            ("Sucursal Base", branch_name),
            ("CURP", self.employee.curp or "-"),
            ("RFC", self.employee.rfc or "-"),
            ("Correo Electrónico", self.employee.email or "-"),
            ("Teléfono de Contacto", self.employee.phone_number or "-"),
            ("Contraseña Numérica de Reloj", pwd_display),
            ("Tarjeta RFID / Proximidad", self.employee.card_number or "-"),
            ("Huellas Biométricas", fp_display),
            ("Estado", "ACTIVO" if self.employee.active else "BAJA / INACTIVO"),
        ]

        table.setRowCount(len(rows))
        for r_idx, (prop, val) in enumerate(rows):
            table.setItem(r_idx, 0, QTableWidgetItem(prop))
            val_item = QTableWidgetItem(val)
            if prop == "Estado":
                val_item.setForeground(
                    Qt.GlobalColor.green if self.employee.active else Qt.GlobalColor.gray
                )
            table.setItem(r_idx, 1, val_item)

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)


class EmployeeEditDialog(QDialog):
    """Modal para dar de alta o editar un colaborador con pestañas por categoría."""

    def __init__(
        self, app_state: AppState, employee: Employee | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.employee = employee
        self.setWindowTitle("Editar Colaborador" if employee else "Nuevo Colaborador")
        self.setMinimumWidth(560)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        self.form_tabs = QTabWidget()
        layout.addWidget(self.form_tabs)

        # 1. Pestaña: Datos Personales
        tab_personal = QWidget()
        form_personal = QFormLayout(tab_personal)
        self.txt_pin = QLineEdit(self.employee.pin if self.employee else "")
        self.txt_first_name = QLineEdit(self.employee.first_name if self.employee else "")
        self.txt_paternal = QLineEdit(self.employee.paternal_last_name if self.employee else "")
        self.txt_maternal = QLineEdit(
            self.employee.maternal_last_name or "" if self.employee else ""
        )

        self.combo_sex = QComboBox()
        self.combo_sex.addItem("Masculino", Sex.MALE)
        self.combo_sex.addItem("Femenino", Sex.FEMALE)
        if self.employee and self.employee.sex == Sex.FEMALE:
            self.combo_sex.setCurrentIndex(1)

        self.date_hire = QDateEdit()
        self.date_hire.setCalendarPopup(True)
        h_date = self.employee.hire_date if self.employee else date.today()
        self.date_hire.setDate(QDate(h_date.year, h_date.month, h_date.day))

        form_personal.addRow("PIN / ID Biométrico (*):", self.txt_pin)
        form_personal.addRow("Nombre(s) (*):", self.txt_first_name)
        form_personal.addRow("Apellido Paterno (*):", self.txt_paternal)
        form_personal.addRow("Apellido Materno:", self.txt_maternal)
        form_personal.addRow("Sexo:", self.combo_sex)
        form_personal.addRow("Fecha de Ingreso:", self.date_hire)
        self.form_tabs.addTab(tab_personal, "Datos Personales")

        # 2. Pestaña: Identificación Fiscal y Contacto
        tab_fiscal = QWidget()
        form_fiscal = QFormLayout(tab_fiscal)
        self.txt_curp = QLineEdit(self.employee.curp or "" if self.employee else "")
        self.txt_curp.setPlaceholderText("18 caracteres alfanuméricos")
        self.txt_rfc = QLineEdit(self.employee.rfc or "" if self.employee else "")
        self.txt_rfc.setPlaceholderText("13 caracteres SAT")
        self.txt_email = QLineEdit(self.employee.email or "" if self.employee else "")
        self.txt_email.setPlaceholderText("ejemplo@empresa.com")
        self.txt_phone = QLineEdit(self.employee.phone_number or "" if self.employee else "")
        self.txt_phone.setPlaceholderText("10 a 15 dígitos")

        form_fiscal.addRow("CURP:", self.txt_curp)
        form_fiscal.addRow("RFC:", self.txt_rfc)
        form_fiscal.addRow("Correo Electrónico:", self.txt_email)
        form_fiscal.addRow("Teléfono de Contacto:", self.txt_phone)
        self.form_tabs.addTab(tab_fiscal, "Fiscal y Contacto")

        # 3. Pestaña: Organización y Puesto
        tab_org = QWidget()
        form_org = QFormLayout(tab_org)
        self.combo_position = QComboBox()
        self.combo_branch = QComboBox()
        self.combo_dept = QComboBox()
        self._load_catalogs()

        form_org.addRow("Puesto / Cargo:", self.combo_position)
        form_org.addRow("Sucursal Base (*):", self.combo_branch)
        form_org.addRow("Departamento (*):", self.combo_dept)
        self.form_tabs.addTab(tab_org, "Organización")

        # 4. Pestaña: Acceso a Terminales (Hardware)
        tab_hw = QWidget()
        form_hw = QFormLayout(tab_hw)
        self.txt_password = QLineEdit(self.employee.password or "" if self.employee else "")
        self.txt_password.setPlaceholderText("Contraseña numérica en reloj (1-8 dígitos)")
        self.txt_card = QLineEdit(self.employee.card_number or "" if self.employee else "")
        self.txt_card.setPlaceholderText("Número de tarjeta RFID")

        self.chk_active = QCheckBox("Colaborador Activo en Plantilla")
        self.chk_active.setChecked(self.employee.active if self.employee else True)

        form_hw.addRow("Clave en Reloj Checador:", self.txt_password)
        form_hw.addRow("Tarjeta RFID / Proximidad:", self.txt_card)
        form_hw.addRow("Estado Laboral:", self.chk_active)
        self.form_tabs.addTab(tab_hw, "Credenciales de Reloj")

        # Botones de acción
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Guardar Colaborador")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._on_save)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _load_catalogs(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        branches = bundle.branch_repo.list_all()
        for b in branches:
            if b.id is not None:
                self.combo_branch.addItem(b.name, b.id)

        depts = bundle.department_repo.list_all()
        if not depts:
            default_dept = Department(id=None, name="General", code="GEN", active=True)
            saved_dept = bundle.department_repo.save(default_dept)
            depts = [saved_dept]

        for d in depts:
            if d.id is not None:
                self.combo_dept.addItem(d.name, d.id)

        positions = bundle.position_repo.list_all() if bundle.position_repo else []
        self.combo_position.addItem("Sin puesto asignado", None)
        for p in positions:
            if p.id is not None:
                self.combo_position.addItem(p.name, p.id)

        if self.employee:
            for i in range(self.combo_branch.count()):
                if self.combo_branch.itemData(i) == self.employee.home_branch_id:
                    self.combo_branch.setCurrentIndex(i)
                    break
            for i in range(self.combo_dept.count()):
                if self.combo_dept.itemData(i) == self.employee.department_id:
                    self.combo_dept.setCurrentIndex(i)
                    break
            for i in range(self.combo_position.count()):
                if self.combo_position.itemData(i) == self.employee.position_id:
                    self.combo_position.setCurrentIndex(i)
                    break

    def _on_save(self) -> None:
        pin = self.txt_pin.text().strip()
        first_name = self.txt_first_name.text().strip()
        paternal = self.txt_paternal.text().strip()
        maternal = self.txt_maternal.text().strip() or None
        position_id = self.combo_position.currentData()
        branch_id = self.combo_branch.currentData()
        dept_id = self.combo_dept.currentData()

        curp = self.txt_curp.text().strip() or None
        rfc = self.txt_rfc.text().strip() or None
        email = self.txt_email.text().strip() or None
        phone = self.txt_phone.text().strip() or None
        password = self.txt_password.text().strip() or None
        card = self.txt_card.text().strip() or None
        active = self.chk_active.isChecked()

        if not pin or not first_name or not paternal:
            QMessageBox.warning(
                self, "Campos requeridos", "PIN, Nombre y Apellido Paterno son obligatorios."
            )
            return

        if branch_id is None or dept_id is None:
            QMessageBox.warning(
                self, "Catálogo incompleto", "Debe existir al menos una sucursal y un departamento."
            )
            return

        bundle = self.state.bundle
        if not bundle:
            return

        py_d = self.date_hire.date()
        hire_d = date(py_d.year(), py_d.month(), py_d.day())
        sex = self.combo_sex.currentData()

        try:
            if self.employee:
                self.employee.pin = pin
                self.employee.first_name = first_name
                self.employee.paternal_last_name = paternal
                self.employee.maternal_last_name = maternal
                self.employee.position_id = position_id
                self.employee.sex = sex
                self.employee.hire_date = hire_d
                self.employee.home_branch_id = branch_id
                self.employee.department_id = dept_id
                self.employee.curp = curp
                self.employee.rfc = rfc
                self.employee.email = email
                self.employee.phone_number = phone
                self.employee.password = password
                self.employee.card_number = card
                self.employee.active = active
                bundle.employee_repo.save(self.employee)
            else:
                new_emp = Employee(
                    id=None,
                    pin=pin,
                    first_name=first_name,
                    paternal_last_name=paternal,
                    maternal_last_name=maternal,
                    position_id=position_id,
                    sex=sex,
                    hire_date=hire_d,
                    home_branch_id=branch_id,
                    department_id=dept_id,
                    active=active,
                    curp=curp,
                    rfc=rfc,
                    email=email,
                    phone_number=phone,
                    password=password,
                    card_number=card,
                )
                bundle.employee_repo.save(new_emp)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Error de validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))


# ============================================================================
# DIÁLOGOS DE DEPARTAMENTOS
# ============================================================================


class DepartmentEditDialog(QDialog):
    """Modal para registrar o editar un departamento."""

    def __init__(
        self, app_state: AppState, dept: Department | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.dept = dept
        self.setWindowTitle("Editar Departamento" if dept else "Nuevo Departamento")
        self.setMinimumWidth(440)
        self.setStyleSheet(Theme.get_stylesheet())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        form = QFormLayout()

        self.txt_code = QLineEdit(self.dept.code or "" if self.dept else "TI")
        self.txt_name = QLineEdit(
            self.dept.name if self.dept else "Tecnologías de la Información"
        )

        self.combo_branch = QComboBox()
        self.combo_branch.addItem("Global (Todas las sucursales)", None)
        bundle = self.state.bundle
        if bundle:
            for b in bundle.branch_repo.list_all():
                if b.id is not None:
                    self.combo_branch.addItem(b.name, b.id)

        if self.dept and self.dept.branch_id is not None:
            for i in range(self.combo_branch.count()):
                if self.combo_branch.itemData(i) == self.dept.branch_id:
                    self.combo_branch.setCurrentIndex(i)
                    break

        self.chk_active = QCheckBox("Departamento Activo")
        self.chk_active.setChecked(self.dept.active if self.dept else True)

        form.addRow("Código de Área:", self.txt_code)
        form.addRow("Nombre (*):", self.txt_name)
        form.addRow("Sucursal Asignada:", self.combo_branch)
        form.addRow("Estado:", self.chk_active)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        code = self.txt_code.text().strip() or None
        branch_id = self.combo_branch.currentData()
        active = self.chk_active.isChecked()

        if not name:
            QMessageBox.warning(self, "Campos requeridos", "El nombre del departamento es obligatorio.")
            return

        bundle = self.state.bundle
        if not bundle:
            return

        try:
            if self.dept:
                self.dept.name = name
                self.dept.code = code
                self.dept.branch_id = branch_id
                self.dept.active = active
                bundle.department_repo.save(self.dept)
            else:
                new_d = Department(id=None, name=name, code=code, branch_id=branch_id, active=active)
                bundle.department_repo.save(new_d)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar departamento", str(e))


# ============================================================================
# DIÁLOGOS DE SUCURSALES
# ============================================================================


class BranchEditDialog(QDialog):
    """Modal para registrar o editar una sucursal física."""

    def __init__(
        self, app_state: AppState, branch: Branch | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.branch = branch
        self.setWindowTitle("Editar Sucursal" if branch else "Nueva Sucursal")
        self.setMinimumWidth(500)
        self.setStyleSheet(Theme.get_stylesheet())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        form = QFormLayout()

        self.txt_code = QLineEdit(self.branch.code if self.branch else "SUC01")
        self.txt_name = QLineEdit(self.branch.name if self.branch else "Planta Norte")
        self.txt_tz = QLineEdit(
            self.branch.timezone if self.branch else "America/Mexico_City"
        )
        self.txt_phone = QLineEdit(
            self.branch.phone_number or "" if self.branch else ""
        )
        self.txt_phone.setPlaceholderText("Ej. +52 55 1234 5678")
        self.txt_email = QLineEdit(self.branch.email or "" if self.branch else "")
        self.txt_email.setPlaceholderText("contacto@sucursal.com")

        # Dirección
        addr = self.branch.address if self.branch else None
        self.txt_street = QLineEdit(addr.street if addr else "")
        self.txt_city = QLineEdit(addr.municipality if addr else "")
        self.txt_state = QLineEdit(addr.state if addr else "")
        self.txt_zip = QLineEdit(addr.postal_code if addr else "")

        self.chk_active = QCheckBox("Sucursal Operativa / Activa")
        self.chk_active.setChecked(self.branch.active if self.branch else True)

        form.addRow("Código de Sucursal (*):", self.txt_code)
        form.addRow("Nombre de Sucursal (*):", self.txt_name)
        form.addRow("Zona Horaria:", self.txt_tz)
        form.addRow("Teléfono de Contacto:", self.txt_phone)
        form.addRow("Correo Electrónico:", self.txt_email)
        form.addRow("Calle y Número:", self.txt_street)
        form.addRow("Ciudad / Municipio:", self.txt_city)
        form.addRow("Estado:", self.txt_state)
        form.addRow("Código Postal:", self.txt_zip)
        form.addRow("Estado:", self.chk_active)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        code = self.txt_code.text().strip().upper()
        tz = self.txt_tz.text().strip() or "America/Mexico_City"
        phone = self.txt_phone.text().strip() or None
        email = self.txt_email.text().strip() or None
        active = self.chk_active.isChecked()

        street = self.txt_street.text().strip()
        city = self.txt_city.text().strip()
        state = self.txt_state.text().strip()
        postal_code = self.txt_zip.text().strip()

        if not name or not code:
            QMessageBox.warning(
                self, "Campos requeridos", "El código y nombre de la sucursal son obligatorios."
            )
            return

        address = None
        if any([street, city, state, postal_code]):
            address = Address(
                street=street,
                exterior_number="",
                interior_number=None,
                postal_code=postal_code,
                neighborhood="",
                municipality=city,
                state=state,
            )

        bundle = self.state.bundle
        if not bundle:
            return

        try:
            if self.branch:
                self.branch.name = name
                self.branch.code = code
                self.branch.timezone = tz
                self.branch.phone_number = phone
                self.branch.email = email
                self.branch.address = address
                self.branch.active = active
                bundle.branch_repo.save(self.branch)
            else:
                new_b = Branch(
                    id=None,
                    name=name,
                    code=code,
                    timezone=tz,
                    phone_number=phone,
                    email=email,
                    address=address,
                    active=active,
                )
                bundle.branch_repo.save(new_b)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Error de validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar sucursal", str(e))


# ============================================================================
# DIÁLOGOS DE PUESTOS / CARGOS LABORALES
# ============================================================================


class PositionEditDialog(QDialog):
    """Modal para dar de alta o editar un puesto laboral."""

    def __init__(
        self, app_state: AppState, position: Position | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.position = position
        self.setWindowTitle("Editar Puesto" if position else "Nuevo Puesto de Trabajo")
        self.setMinimumWidth(460)
        self.setStyleSheet(Theme.get_stylesheet())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        form = QFormLayout()

        self.txt_code = QLineEdit(self.position.code or "" if self.position else "OPER")
        self.txt_name = QLineEdit(self.position.name if self.position else "Operador General")
        self.txt_desc = QTextEdit(self.position.description or "" if self.position else "")
        self.txt_desc.setMaximumHeight(80)
        self.chk_active = QCheckBox("Puesto Activo")
        self.chk_active.setChecked(self.position.active if self.position else True)

        form.addRow("Código de Puesto:", self.txt_code)
        form.addRow("Nombre del Puesto (*):", self.txt_name)
        form.addRow("Descripción / Funciones:", self.txt_desc)
        form.addRow("Estado:", self.chk_active)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        code = self.txt_code.text().strip().upper() or None
        desc = self.txt_desc.toPlainText().strip() or None
        active = self.chk_active.isChecked()

        if not name:
            QMessageBox.warning(self, "Campos requeridos", "El nombre del puesto es obligatorio.")
            return

        bundle = self.state.bundle
        if not bundle or not bundle.position_repo:
            return

        try:
            if self.position:
                self.position.name = name
                self.position.code = code
                self.position.description = desc
                self.position.active = active
                bundle.position_repo.save(self.position)
            else:
                new_pos = Position(id=None, name=name, code=code, description=desc, active=active)
                bundle.position_repo.save(new_pos)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Error de validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar puesto", str(e))


class PositionAssignDeptDialog(QDialog):
    """Modal para asociar y desasociar departamentos a un puesto (relación N:M)."""

    def __init__(
        self, app_state: AppState, position: Position, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.position = position
        self.setWindowTitle(f"Departamentos para: {position.name}")
        self.setMinimumWidth(420)
        self.setStyleSheet(Theme.get_stylesheet())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel(
            f"Seleccione los departamentos en los que puede desempeñarse el puesto <b>{self.position.name}</b>:"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        bundle = self.state.bundle
        if bundle and bundle.position_repo and self.position.id:
            all_depts = bundle.department_repo.list_all()
            assigned = bundle.position_repo.get_departments(self.position.id)
            assigned_ids = {d.id for d in assigned if d.id is not None}

            for d in all_depts:
                if d.id is not None:
                    item = QListWidgetItem(f"{d.name} ({d.code or 'S/C'})")
                    item.setData(Qt.ItemDataRole.UserRole, d.id)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(
                        Qt.CheckState.Checked if d.id in assigned_ids else Qt.CheckState.Unchecked
                    )
                    self.list_widget.addItem(item)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar Asignaciones")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        bundle = self.state.bundle
        if not bundle or not bundle.position_repo or not self.position.id:
            return

        try:
            current_assigned = bundle.position_repo.get_departments(self.position.id)
            current_ids = {d.id for d in current_assigned if d.id is not None}

            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                dept_id = item.data(Qt.ItemDataRole.UserRole)
                is_checked = item.checkState() == Qt.CheckState.Checked

                if is_checked and dept_id not in current_ids:
                    bundle.position_repo.assign_department(self.position.id, dept_id)
                elif not is_checked and dept_id in current_ids:
                    bundle.position_repo.remove_department(self.position.id, dept_id)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al actualizar asignaciones", str(e))


# ============================================================================
# VISTA PRINCIPAL DE PERSONAL Y ORGANIZACIÓN
# ============================================================================


class EmployeesView(QWidget):
    """Pantalla de organización con pestañas de empleados, puestos, departamentos y sucursales."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._setup_ui()
        self.refresh_all()

        self.state.data_updated.connect(
            lambda k: self.refresh_all() if k in ("all", "employees") else None
        )

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Directorio Organizacional")
        title.setObjectName("h1Title")
        sub = QLabel("Administración de colaboradores, puestos de trabajo, sucursales y áreas.")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_new_emp = QPushButton("+ Nuevo Colaborador")
        self.btn_new_emp.setObjectName("primaryBtn")
        self.btn_new_emp.clicked.connect(self._add_employee)
        top.addWidget(self.btn_new_emp)

        layout.addLayout(top)

        # Pestañas principales
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_employees_tab()
        self._setup_positions_tab()
        self._setup_departments_tab()
        self._setup_branches_tab()

    # ------------------------------------------------------------------------
    # TAB: COLABORADORES
    # ------------------------------------------------------------------------

    def _setup_employees_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        # Filtros
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por PIN, nombre, CURP o RFC...")
        self.txt_search.textChanged.connect(self.refresh_employees)
        filter_bar.addWidget(self.txt_search)

        self.filter_branch = QComboBox()
        self.filter_branch.addItem("Todas las sucursales", None)
        self.filter_branch.currentIndexChanged.connect(self.refresh_employees)
        filter_bar.addWidget(self.filter_branch)

        self.filter_dept = QComboBox()
        self.filter_dept.addItem("Todos los departamentos", None)
        self.filter_dept.currentIndexChanged.connect(self.refresh_employees)
        filter_bar.addWidget(self.filter_dept)

        self.chk_filter_active = QCheckBox("Solo Activos")
        self.chk_filter_active.setChecked(False)
        self.chk_filter_active.toggled.connect(self.refresh_employees)
        filter_bar.addWidget(self.chk_filter_active)

        t_layout.addLayout(filter_bar)

        # Acciones de fila
        action_bar = QHBoxLayout()
        self.btn_detail_emp = QPushButton("👁️ Ver Ficha")
        self.btn_detail_emp.clicked.connect(self._show_employee_detail)
        self.btn_schedule_emp = QPushButton("🗓️ Establecer Horario")
        self.btn_schedule_emp.setObjectName("primaryBtn")
        self.btn_schedule_emp.clicked.connect(self._set_employee_schedule)
        self.btn_edit_emp = QPushButton("✏️ Editar")
        self.btn_edit_emp.clicked.connect(self._edit_employee)
        self.btn_toggle_emp = QPushButton("Activar / Desactivar")
        self.btn_toggle_emp.clicked.connect(self._toggle_employee)
        self.btn_delete_emp = QPushButton("🗑️ Eliminar")
        self.btn_delete_emp.clicked.connect(self._delete_employee)

        action_bar.addWidget(self.btn_detail_emp)
        action_bar.addWidget(self.btn_schedule_emp)
        action_bar.addWidget(self.btn_edit_emp)
        action_bar.addWidget(self.btn_toggle_emp)
        action_bar.addWidget(self.btn_delete_emp)
        action_bar.addStretch()
        t_layout.addLayout(action_bar)

        # Tabla
        self.emp_table = QTableWidget()
        self.emp_table.setColumnCount(8)
        self.emp_table.setHorizontalHeaderLabels(
            ["ID", "PIN", "Nombre Completo", "Puesto", "Departamento", "Sucursal", "RFC / CURP", "Estado"]
        )
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.emp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.emp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.emp_table)

        self.tabs.addTab(tab, "Colaboradores")

    # ------------------------------------------------------------------------
    # TAB: PUESTOS / CARGOS
    # ------------------------------------------------------------------------

    def _setup_positions_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        bar = QHBoxLayout()
        self.btn_new_pos = QPushButton("+ Nuevo Puesto")
        self.btn_new_pos.clicked.connect(self._add_position)
        self.btn_edit_pos = QPushButton("✏️ Editar")
        self.btn_edit_pos.clicked.connect(self._edit_position)
        self.btn_assign_pos_dept = QPushButton("🏢 Departamentos Asignados")
        self.btn_assign_pos_dept.clicked.connect(self._assign_position_dept)
        self.btn_toggle_pos = QPushButton("Activar / Desactivar")
        self.btn_toggle_pos.clicked.connect(self._toggle_position)
        self.btn_delete_pos = QPushButton("🗑️ Eliminar")
        self.btn_delete_pos.clicked.connect(self._delete_position)

        bar.addWidget(self.btn_new_pos)
        bar.addWidget(self.btn_edit_pos)
        bar.addWidget(self.btn_assign_pos_dept)
        bar.addWidget(self.btn_toggle_pos)
        bar.addWidget(self.btn_delete_pos)
        bar.addStretch()
        t_layout.addLayout(bar)

        self.pos_table = QTableWidget()
        self.pos_table.setColumnCount(6)
        self.pos_table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre del Puesto", "Descripción", "Deptos. Vinculados", "Estado"]
        )
        self.pos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pos_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.pos_table)

        self.tabs.addTab(tab, "Puestos / Cargos")

    # ------------------------------------------------------------------------
    # TAB: DEPARTAMENTOS
    # ------------------------------------------------------------------------

    def _setup_departments_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        bar = QHBoxLayout()
        self.btn_new_dept = QPushButton("+ Nuevo Departamento")
        self.btn_new_dept.clicked.connect(self._add_department)
        self.btn_edit_dept = QPushButton("✏️ Editar")
        self.btn_edit_dept.clicked.connect(self._edit_department)
        self.btn_toggle_dept = QPushButton("Activar / Desactivar")
        self.btn_toggle_dept.clicked.connect(self._toggle_department)
        self.btn_delete_dept = QPushButton("🗑️ Eliminar")
        self.btn_delete_dept.clicked.connect(self._delete_department)

        bar.addWidget(self.btn_new_dept)
        bar.addWidget(self.btn_edit_dept)
        bar.addWidget(self.btn_toggle_dept)
        bar.addWidget(self.btn_delete_dept)
        bar.addStretch()
        t_layout.addLayout(bar)

        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(6)
        self.dept_table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre", "Sucursal Asignada", "Puestos Asociados", "Estado"]
        )
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dept_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.dept_table)

        self.tabs.addTab(tab, "Departamentos")

    # ------------------------------------------------------------------------
    # TAB: SUCURSALES
    # ------------------------------------------------------------------------

    def _setup_branches_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        bar = QHBoxLayout()
        self.btn_new_branch = QPushButton("+ Nueva Sucursal")
        self.btn_new_branch.clicked.connect(self._add_branch)
        self.btn_edit_branch = QPushButton("✏️ Editar")
        self.btn_edit_branch.clicked.connect(self._edit_branch)
        self.btn_toggle_branch = QPushButton("Activar / Desactivar")
        self.btn_toggle_branch.clicked.connect(self._toggle_branch)
        self.btn_delete_branch = QPushButton("🗑️ Eliminar")
        self.btn_delete_branch.clicked.connect(self._delete_branch)

        bar.addWidget(self.btn_new_branch)
        bar.addWidget(self.btn_edit_branch)
        bar.addWidget(self.btn_toggle_branch)
        bar.addWidget(self.btn_delete_branch)
        bar.addStretch()
        t_layout.addLayout(bar)

        self.branch_table = QTableWidget()
        self.branch_table.setColumnCount(7)
        self.branch_table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre de Sucursal", "Zona Horaria", "Ubicación", "Teléfono", "Estado"]
        )
        self.branch_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.branch_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.branch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.branch_table)

        self.tabs.addTab(tab, "Sucursales")

    # ========================================================================
    # MÉTODOS DE ACTUALIZACIÓN Y REFRESCO
    # ========================================================================

    def refresh_all(self) -> None:
        self._refresh_filter_combos()
        self.refresh_employees()
        self.refresh_positions()
        self.refresh_departments()
        self.refresh_branches()

    def _refresh_filter_combos(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        # Guardar selecciones actuales
        curr_branch = self.filter_branch.currentData()
        curr_dept = self.filter_dept.currentData()

        self.filter_branch.blockSignals(True)
        self.filter_branch.clear()
        self.filter_branch.addItem("Todas las sucursales", None)
        for b in bundle.branch_repo.list_all():
            if b.id is not None:
                self.filter_branch.addItem(b.name, b.id)
                if b.id == curr_branch:
                    self.filter_branch.setCurrentIndex(self.filter_branch.count() - 1)
        self.filter_branch.blockSignals(False)

        self.filter_dept.blockSignals(True)
        self.filter_dept.clear()
        self.filter_dept.addItem("Todos los departamentos", None)
        for d in bundle.department_repo.list_all():
            if d.id is not None:
                self.filter_dept.addItem(d.name, d.id)
                if d.id == curr_dept:
                    self.filter_dept.setCurrentIndex(self.filter_dept.count() - 1)
        self.filter_dept.blockSignals(False)

    def refresh_employees(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        try:
            branch_id = self.filter_branch.currentData()
            dept_id = self.filter_dept.currentData()
            active_only = self.chk_filter_active.isChecked()

            employees = bundle.employee_repo.list_all(
                branch_id=branch_id,
                department_id=dept_id,
                active_only=active_only,
            )
            depts = {d.id: d.name for d in bundle.department_repo.list_all() if d.id is not None}
            branches = {b.id: b.name for b in bundle.branch_repo.list_all() if b.id is not None}
            positions = (
                {p.id: p.name for p in bundle.position_repo.list_all() if p.id is not None}
                if bundle.position_repo
                else {}
            )

            query = self.txt_search.text().strip().lower()
            if query:
                employees = [
                    e
                    for e in employees
                    if query in e.pin.lower()
                    or query in e.full_name.lower()
                    or (e.curp and query in e.curp.lower())
                    or (e.rfc and query in e.rfc.lower())
                    or (e.card_number and query in e.card_number.lower())
                ]

            self.emp_table.setRowCount(len(employees))
            for row, emp in enumerate(employees):
                self.emp_table.setItem(row, 0, QTableWidgetItem(str(emp.id or "-")))
                self.emp_table.setItem(row, 1, QTableWidgetItem(emp.pin))
                self.emp_table.setItem(row, 2, QTableWidgetItem(emp.full_name))
                pos_display = positions.get(emp.position_id, "-") if emp.position_id else "-"
                self.emp_table.setItem(row, 3, QTableWidgetItem(pos_display))
                self.emp_table.setItem(
                    row, 4, QTableWidgetItem(depts.get(emp.department_id, "N/A"))
                )
                self.emp_table.setItem(
                    row, 5, QTableWidgetItem(branches.get(emp.home_branch_id, "N/A"))
                )
                rfc_curp = emp.rfc or emp.curp or "-"
                self.emp_table.setItem(row, 6, QTableWidgetItem(rfc_curp))

                status_item = QTableWidgetItem("ACTIVO" if emp.active else "BAJA")
                status_item.setForeground(
                    Qt.GlobalColor.green if emp.active else Qt.GlobalColor.gray
                )
                self.emp_table.setItem(row, 7, status_item)
        except Exception:
            pass

    def refresh_positions(self) -> None:
        bundle = self.state.bundle
        if not bundle or not bundle.position_repo:
            return
        try:
            positions = bundle.position_repo.list_all()
            self.pos_table.setRowCount(len(positions))
            for row, p in enumerate(positions):
                self.pos_table.setItem(row, 0, QTableWidgetItem(str(p.id or "-")))
                self.pos_table.setItem(row, 1, QTableWidgetItem(p.code or "-"))
                self.pos_table.setItem(row, 2, QTableWidgetItem(p.name))
                self.pos_table.setItem(row, 3, QTableWidgetItem(p.description or "-"))

                depts = bundle.position_repo.get_departments(p.id) if p.id else []
                depts_str = ", ".join(d.name for d in depts) if depts else "Ninguno"
                self.pos_table.setItem(row, 4, QTableWidgetItem(depts_str))

                status_item = QTableWidgetItem("ACTIVO" if p.active else "INACTIVO")
                status_item.setForeground(Qt.GlobalColor.green if p.active else Qt.GlobalColor.gray)
                self.pos_table.setItem(row, 5, status_item)
        except Exception:
            pass

    def refresh_departments(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            depts = bundle.department_repo.list_all()
            branches_map = {b.id: b.name for b in bundle.branch_repo.list_all() if b.id is not None}
            self.dept_table.setRowCount(len(depts))
            for row, d in enumerate(depts):
                self.dept_table.setItem(row, 0, QTableWidgetItem(str(d.id or "-")))
                self.dept_table.setItem(row, 1, QTableWidgetItem(d.code or "-"))
                self.dept_table.setItem(row, 2, QTableWidgetItem(d.name))

                branch_str = (
                    branches_map.get(d.branch_id, f"Sucursal #{d.branch_id}")
                    if d.branch_id
                    else "Global (Todas)"
                )
                self.dept_table.setItem(row, 3, QTableWidgetItem(branch_str))

                pos_list = (
                    bundle.department_repo.get_positions(d.id)
                    if (d.id and hasattr(bundle.department_repo, "get_positions"))
                    else []
                )
                pos_str = ", ".join(p.name for p in pos_list) if pos_list else "Ninguno"
                self.dept_table.setItem(row, 4, QTableWidgetItem(pos_str))

                status_item = QTableWidgetItem("ACTIVO" if d.active else "INACTIVO")
                status_item.setForeground(Qt.GlobalColor.green if d.active else Qt.GlobalColor.gray)
                self.dept_table.setItem(row, 5, status_item)
        except Exception:
            pass

    def refresh_branches(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            branches = bundle.branch_repo.list_all()
            self.branch_table.setRowCount(len(branches))
            for row, b in enumerate(branches):
                self.branch_table.setItem(row, 0, QTableWidgetItem(str(b.id or "-")))
                self.branch_table.setItem(row, 1, QTableWidgetItem(b.code))
                self.branch_table.setItem(row, 2, QTableWidgetItem(b.name))
                self.branch_table.setItem(row, 3, QTableWidgetItem(b.timezone))

                loc_str = "-"
                if b.address:
                    loc_parts = [p for p in [b.address.municipality, b.address.state] if p]
                    loc_str = ", ".join(loc_parts) if loc_parts else "-"
                self.branch_table.setItem(row, 4, QTableWidgetItem(loc_str))

                phone_str = b.phone_number or "-"
                self.branch_table.setItem(row, 5, QTableWidgetItem(phone_str))

                status_item = QTableWidgetItem("ACTIVO" if b.active else "INACTIVO")
                status_item.setForeground(Qt.GlobalColor.green if b.active else Qt.GlobalColor.gray)
                self.branch_table.setItem(row, 6, status_item)
        except Exception:
            pass

    # ========================================================================
    # ACCIONES: COLABORADORES
    # ========================================================================

    def _get_selected_employee(self) -> Employee | None:
        row = self.emp_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un colaborador de la lista.")
            return None
        pin_item = self.emp_table.item(row, 1)
        if not pin_item or not pin_item.text() or not self.state.bundle:
            return None
        return self.state.bundle.employee_repo.get_by_pin(pin_item.text())

    def _show_employee_detail(self) -> None:
        emp = self._get_selected_employee()
        if not emp:
            return
        dialog = EmployeeDetailDialog(self.state, employee=emp, parent=self)
        dialog.exec()

    def _set_employee_schedule(self) -> None:
        emp = self._get_selected_employee()
        pin = emp.pin if emp else None
        dialog = SetEmployeeScheduleDialog(self.state, preset_employee_pin=pin, parent=self)
        dialog.exec()

    def _add_employee(self) -> None:
        dialog = EmployeeEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Colaborador registrado exitosamente.", "success")

    def _edit_employee(self) -> None:
        emp = self._get_selected_employee()
        if not emp:
            return
        dialog = EmployeeEditDialog(self.state, employee=emp, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Colaborador actualizado.", "success")

    def _toggle_employee(self) -> None:
        emp = self._get_selected_employee()
        if not emp or not self.state.bundle:
            return
        emp.active = not emp.active
        self.state.bundle.employee_repo.save(emp)
        self.refresh_employees()
        self.state.data_updated.emit("employees")
        self.state.notify(
            f"Colaborador {'reactivado' if emp.active else 'dado de baja'}.", "info"
        )

    def _delete_employee(self) -> None:
        emp = self._get_selected_employee()
        if not emp or not self.state.bundle:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar al colaborador '{emp.full_name}' (PIN: {emp.pin}) permanentemente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.employee_repo.delete(emp.pin)
            if success:
                self.refresh_employees()
                self.state.data_updated.emit("employees")
                self.state.notify(f"Colaborador {emp.pin} eliminado.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el colaborador.")

    # ========================================================================
    # ACCIONES: PUESTOS / CARGOS
    # ========================================================================

    def _get_selected_position(self) -> Position | None:
        row = self.pos_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un puesto de la lista.")
            return None
        id_item = self.pos_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle or not self.state.bundle.position_repo:
            return None
        return self.state.bundle.position_repo.get_by_id(int(id_item.text()))

    def _add_position(self) -> None:
        dialog = PositionEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_positions()
            self._refresh_filter_combos()
            self.state.data_updated.emit("employees")
            self.state.notify("Puesto registrado exitosamente.", "success")

    def _edit_position(self) -> None:
        pos = self._get_selected_position()
        if not pos:
            return
        dialog = PositionEditDialog(self.state, position=pos, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_positions()
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Puesto actualizado.", "success")

    def _assign_position_dept(self) -> None:
        pos = self._get_selected_position()
        if not pos:
            return
        dialog = PositionAssignDeptDialog(self.state, position=pos, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_positions()
            self.refresh_departments()
            self.state.notify(f"Departamentos actualizados para el puesto '{pos.name}'.", "success")

    def _toggle_position(self) -> None:
        pos = self._get_selected_position()
        if not pos or not self.state.bundle or not self.state.bundle.position_repo:
            return
        pos.active = not pos.active
        self.state.bundle.position_repo.save(pos)
        self.refresh_positions()
        self.state.notify(f"Puesto '{pos.name}' {'activado' if pos.active else 'desactivado'}.", "info")

    def _delete_position(self) -> None:
        pos = self._get_selected_position()
        if not pos or not pos.id or not self.state.bundle or not self.state.bundle.position_repo:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el puesto '{pos.name}' (ID: {pos.id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.position_repo.delete(pos.id)
            if success:
                self.refresh_positions()
                self.refresh_employees()
                self.state.data_updated.emit("employees")
                self.state.notify(f"Puesto '{pos.name}' eliminado.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el puesto.")

    # ========================================================================
    # ACCIONES: DEPARTAMENTOS
    # ========================================================================

    def _get_selected_department(self) -> Department | None:
        row = self.dept_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un departamento de la lista.")
            return None
        id_item = self.dept_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle:
            return None
        return self.state.bundle.department_repo.get_by_id(int(id_item.text()))

    def _add_department(self) -> None:
        dialog = DepartmentEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_departments()
            self._refresh_filter_combos()
            self.state.data_updated.emit("employees")
            self.state.notify("Departamento registrado exitosamente.", "success")

    def _edit_department(self) -> None:
        dept = self._get_selected_department()
        if not dept:
            return
        dialog = DepartmentEditDialog(self.state, dept=dept, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_departments()
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Departamento actualizado.", "success")

    def _toggle_department(self) -> None:
        dept = self._get_selected_department()
        if not dept or not self.state.bundle:
            return
        dept.active = not dept.active
        self.state.bundle.department_repo.save(dept)
        self.refresh_departments()
        self.state.notify(
            f"Departamento '{dept.name}' {'activado' if dept.active else 'desactivado'}.", "info"
        )

    def _delete_department(self) -> None:
        dept = self._get_selected_department()
        if not dept or not dept.id or not self.state.bundle:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el departamento '{dept.name}' (ID: {dept.id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.department_repo.delete(dept.id)
            if success:
                self.refresh_departments()
                self._refresh_filter_combos()
                self.refresh_employees()
                self.state.data_updated.emit("employees")
                self.state.notify(f"Departamento '{dept.name}' eliminado.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el departamento.")

    # ========================================================================
    # ACCIONES: SUCURSALES
    # ========================================================================

    def _get_selected_branch(self) -> Branch | None:
        row = self.branch_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione una sucursal de la lista.")
            return None
        id_item = self.branch_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle:
            return None
        return self.state.bundle.branch_repo.get_by_id(int(id_item.text()))

    def _add_branch(self) -> None:
        dialog = BranchEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_branches()
            self._refresh_filter_combos()
            self.state.data_updated.emit("employees")
            self.state.notify("Sucursal registrada exitosamente.", "success")

    def _edit_branch(self) -> None:
        branch = self._get_selected_branch()
        if not branch:
            return
        dialog = BranchEditDialog(self.state, branch=branch, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_branches()
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Sucursal actualizada.", "success")

    def _toggle_branch(self) -> None:
        branch = self._get_selected_branch()
        if not branch or not self.state.bundle:
            return
        branch.active = not branch.active
        self.state.bundle.branch_repo.save(branch)
        self.refresh_branches()
        self.state.notify(
            f"Sucursal '{branch.name}' {'activada' if branch.active else 'desactivada'}.", "info"
        )

    def _delete_branch(self) -> None:
        branch = self._get_selected_branch()
        if not branch or not branch.id or not self.state.bundle:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar la sucursal '{branch.name}' (ID: {branch.id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.branch_repo.delete(branch.id)
            if success:
                self.refresh_branches()
                self._refresh_filter_combos()
                self.refresh_employees()
                self.state.data_updated.emit("employees")
                self.state.notify(f"Sucursal '{branch.name}' eliminada.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar la sucursal.")

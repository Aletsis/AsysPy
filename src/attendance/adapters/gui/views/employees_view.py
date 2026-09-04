"""Vista de Gestión de Personal y Organización (Empleados, Departamentos, Sucursales)."""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.domain.organization.branch import Branch
from attendance.domain.organization.department import Department
from attendance.domain.organization.employee import Employee, Sex


class EmployeeEditDialog(QDialog):
    """Modal para dar de alta o editar un empleado."""

    def __init__(
        self, app_state: AppState, employee: Employee | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.employee = employee
        self.setWindowTitle("Editar Colaborador" if employee else "Nuevo Colaborador")
        self.setMinimumWidth(500)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
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

        self.combo_branch = QComboBox()
        self.combo_dept = QComboBox()
        self.combo_position = QComboBox()
        self._load_catalogs()

        form.addRow("PIN / ID Biométrico:", self.txt_pin)
        form.addRow("Nombre(s):", self.txt_first_name)
        form.addRow("Apellido Paterno:", self.txt_paternal)
        form.addRow("Apellido Materno:", self.txt_maternal)
        form.addRow("Sexo:", self.combo_sex)
        form.addRow("Fecha de Ingreso:", self.date_hire)
        form.addRow("Puesto de Trabajo:", self.combo_position)
        form.addRow("Sucursal Base:", self.combo_branch)
        form.addRow("Departamento:", self.combo_dept)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Guardar")
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
            # Si no hay departamentos, crear uno por defecto
            default_dept = Department(id=None, name="General", code="GEN", active=True)
            saved_dept = bundle.department_repo.save(default_dept)
            depts = [saved_dept]

        for d in depts:
            if d.id is not None:
                self.combo_dept.addItem(d.name, d.id)

        positions = bundle.position_repo.list_all() if bundle.position_repo else []
        self.combo_position.addItem("Sin puesto", None)
        for p in positions:
            if p.id is not None:
                self.combo_position.addItem(p.name, p.id)

        if self.employee:
            # Seleccionar sucursal
            for i in range(self.combo_branch.count()):
                if self.combo_branch.itemData(i) == self.employee.home_branch_id:
                    self.combo_branch.setCurrentIndex(i)
                    break
            # Seleccionar dpto
            for i in range(self.combo_dept.count()):
                if self.combo_dept.itemData(i) == self.employee.department_id:
                    self.combo_dept.setCurrentIndex(i)
                    break
            # Seleccionar puesto
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
                    active=True,
                )
                bundle.employee_repo.save(new_emp)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))


class EmployeesView(QWidget):
    """Pantalla de organización con pestañas de empleados, departamentos y sucursales."""

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
        sub = QLabel("Administración de colaboradores, sucursales y áreas.")
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

        # Pestañas
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_employees_tab()
        self._setup_departments_tab()
        self._setup_branches_tab()

    def _setup_employees_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        # Filtro de búsqueda
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por PIN, nombre o apellido...")
        self.txt_search.textChanged.connect(self.refresh_employees)
        filter_bar.addWidget(self.txt_search)

        self.btn_edit_emp = QPushButton("✏️ Editar")
        self.btn_edit_emp.clicked.connect(self._edit_employee)
        self.btn_toggle_emp = QPushButton("Activar / Desactivar")
        self.btn_toggle_emp.clicked.connect(self._toggle_employee)

        filter_bar.addWidget(self.btn_edit_emp)
        filter_bar.addWidget(self.btn_toggle_emp)
        t_layout.addLayout(filter_bar)

        # Tabla
        self.emp_table = QTableWidget()
        self.emp_table.setColumnCount(7)
        self.emp_table.setHorizontalHeaderLabels(
            ["ID", "PIN", "Nombre Completo", "Puesto", "Departamento", "Sucursal", "Estado"]
        )
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.emp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.emp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.emp_table)

        self.tabs.addTab(tab, "Colaboradores")

    def _setup_departments_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        bar = QHBoxLayout()
        self.btn_new_dept = QPushButton("+ Nuevo Departamento")
        self.btn_new_dept.clicked.connect(self._add_department)
        bar.addWidget(self.btn_new_dept)
        bar.addStretch()
        t_layout.addLayout(bar)

        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(4)
        self.dept_table.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Estado"])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dept_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.dept_table)

        self.tabs.addTab(tab, "Departamentos")

    def _setup_branches_tab(self) -> None:
        tab = QWidget()
        t_layout = QVBoxLayout(tab)
        t_layout.setSpacing(12)

        bar = QHBoxLayout()
        self.btn_new_branch = QPushButton("+ Nueva Sucursal")
        self.btn_new_branch.clicked.connect(self._add_branch)
        bar.addWidget(self.btn_new_branch)
        bar.addStretch()
        t_layout.addLayout(bar)

        self.branch_table = QTableWidget()
        self.branch_table.setColumnCount(3)
        self.branch_table.setHorizontalHeaderLabels(["ID", "Nombre de Sucursal", "Zona Horaria"])
        self.branch_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.branch_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.branch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_layout.addWidget(self.branch_table)

        self.tabs.addTab(tab, "Sucursales")

    def refresh_all(self) -> None:
        self.refresh_employees()
        self.refresh_departments()
        self.refresh_branches()

    def refresh_employees(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        try:
            employees = bundle.employee_repo.list_all()
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
                    or (e.position_id and query in positions.get(e.position_id, "").lower())
                ]

            self.emp_table.setRowCount(len(employees))
            for row, emp in enumerate(employees):
                self.emp_table.setItem(row, 0, QTableWidgetItem(str(emp.id)))
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

                status_item = QTableWidgetItem("ACTIVO" if emp.active else "BAJA")
                status_item.setForeground(
                    Qt.GlobalColor.green if emp.active else Qt.GlobalColor.gray
                )
                self.emp_table.setItem(row, 6, status_item)
        except Exception:
            pass

    def refresh_departments(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            depts = bundle.department_repo.list_all()
            self.dept_table.setRowCount(len(depts))
            for row, d in enumerate(depts):
                self.dept_table.setItem(row, 0, QTableWidgetItem(str(d.id)))
                self.dept_table.setItem(row, 1, QTableWidgetItem(d.code or "-"))
                self.dept_table.setItem(row, 2, QTableWidgetItem(d.name))
                status_item = QTableWidgetItem("ACTIVO" if d.active else "INACTIVO")
                status_item.setForeground(Qt.GlobalColor.green if d.active else Qt.GlobalColor.gray)
                self.dept_table.setItem(row, 3, status_item)
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
                self.branch_table.setItem(row, 0, QTableWidgetItem(str(b.id)))
                self.branch_table.setItem(row, 1, QTableWidgetItem(b.name))
                self.branch_table.setItem(row, 2, QTableWidgetItem(b.timezone))
        except Exception:
            pass

    def _add_employee(self) -> None:
        dialog = EmployeeEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Colaborador registrado exitosamente.", "success")

    def _edit_employee(self) -> None:
        row = self.emp_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un colaborador para editar.")
            return
        item = self.emp_table.item(row, 0)
        if not item or not item.text():
            return
        emp_id = int(item.text())
        emp = self.state.bundle.employee_repo.get_by_id(emp_id) if self.state.bundle else None
        if not emp:
            return
        dialog = EmployeeEditDialog(self.state, employee=emp, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify("Colaborador actualizado.", "success")

    def _toggle_employee(self) -> None:
        row = self.emp_table.currentRow()
        if row < 0:
            return
        item = self.emp_table.item(row, 0)
        if not item or not item.text() or not self.state.bundle:
            return
        emp_id = int(item.text())
        emp = self.state.bundle.employee_repo.get_by_id(emp_id)
        if emp:
            emp.active = not emp.active
            self.state.bundle.employee_repo.save(emp)
            self.refresh_employees()
            self.state.data_updated.emit("employees")
            self.state.notify(
                f"Colaborador {'reactivado' if emp.active else 'dado de baja'}.", "info"
            )

    def _add_department(self) -> None:
        if not self.state.bundle:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuevo Departamento")
        dialog.setStyleSheet(Theme.get_stylesheet())
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        txt_code = QLineEdit("TI")
        txt_name = QLineEdit("Tecnologías de la Información")
        form.addRow("Código:", txt_code)
        form.addRow("Nombre:", txt_name)
        layout.addLayout(form)

        btns = QHBoxLayout()
        b_save = QPushButton("Guardar")
        b_save.setObjectName("primaryBtn")
        b_save.clicked.connect(dialog.accept)
        btns.addWidget(b_save)
        layout.addLayout(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted and txt_name.text().strip():
            dept = Department(
                id=None, code=txt_code.text().strip(), name=txt_name.text().strip(), active=True
            )
            self.state.bundle.department_repo.save(dept)
            self.refresh_departments()
            self.state.notify(f"Departamento '{dept.name}' creado.", "success")

    def _add_branch(self) -> None:
        if not self.state.bundle:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Nueva Sucursal")
        dialog.setStyleSheet(Theme.get_stylesheet())
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        txt_name = QLineEdit("Planta Norte")
        txt_tz = QLineEdit("America/Mexico_City")
        form.addRow("Nombre de Sucursal:", txt_name)
        form.addRow("Zona Horaria:", txt_tz)
        layout.addLayout(form)

        btns = QHBoxLayout()
        b_save = QPushButton("Guardar")
        b_save.setObjectName("primaryBtn")
        b_save.clicked.connect(dialog.accept)
        btns.addWidget(b_save)
        layout.addLayout(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted and txt_name.text().strip():
            code = (txt_name.text().strip()[:4] or "SUC").upper()
            branch = Branch(
                id=None, name=txt_name.text().strip(), code=code, timezone=txt_tz.text().strip()
            )
            self.state.bundle.branch_repo.save(branch)
            self.refresh_branches()
            self.state.notify(f"Sucursal '{branch.name}' creada.", "success")

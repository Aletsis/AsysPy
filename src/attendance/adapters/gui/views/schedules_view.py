"""Vista de Gestión de Turnos y Asignación de Horarios."""

from datetime import date, time

from PySide6.QtCore import QDate, QTime
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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, ShiftCategory
from attendance.domain.schedule.shift import ShiftDefinition


class ShiftEditDialog(QDialog):
    """Modal para registrar o editar un turno de trabajo."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self.setWindowTitle("Nuevo Turno de Trabajo")
        self.setMinimumWidth(440)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.txt_name = QLineEdit("Matutino 08:00 - 16:00")

        self.time_start = QTimeEdit()
        self.time_start.setTime(QTime(8, 0))

        self.time_end = QTimeEdit()
        self.time_end.setTime(QTime(16, 0))

        self.spin_tolerance = QSpinBox()
        self.spin_tolerance.setRange(0, 120)
        self.spin_tolerance.setValue(10)
        self.spin_tolerance.setSuffix(" min")

        self.chk_midnight = QCheckBox("Cruza la medianoche (Jornada Nocturna)")

        form.addRow("Nombre del Turno:", self.txt_name)
        form.addRow("Hora de Entrada:", self.time_start)
        form.addRow("Hora de Salida:", self.time_end)
        form.addRow("Tolerancia de Entrada:", self.spin_tolerance)
        form.addRow("", self.chk_midnight)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar Turno")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Campos requeridos", "El nombre del turno es obligatorio.")
            return

        bundle = self.state.bundle
        if not bundle:
            return

        st = self.time_start.time()
        et = self.time_end.time()
        start_t = time(st.hour(), st.minute(), st.second())
        end_t = time(et.hour(), et.minute(), et.second())
        tol = self.spin_tolerance.value()
        midnight = self.chk_midnight.isChecked()

        try:
            shift = ShiftDefinition(
                id=None,
                name=name,
                category=ShiftCategory.PERSONALIZADO,
                start_time=start_t,
                end_time=end_t,
                tolerance_minutes=tol,
                crosses_midnight=midnight,
            )
            bundle.shift_repo.save(shift)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar turno", str(e))


class AssignmentDialog(QDialog):
    """Modal para asignar un turno a un empleado."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self.setWindowTitle("Asignar Horario a Colaborador")
        self.setMinimumWidth(460)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.combo_emp = QComboBox()
        self.combo_shift = QComboBox()
        self._load_combos()

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        td = date.today()
        self.date_from.setDate(QDate(td.year, td.month, td.day))

        form.addRow("Colaborador:", self.combo_emp)
        form.addRow("Turno a Asignar:", self.combo_shift)
        form.addRow("Vigente a partir de:", self.date_from)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Asignar")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _load_combos(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        employees = bundle.employee_repo.list_all()
        for e in employees:
            self.combo_emp.addItem(f"{e.pin} - {e.full_name}", e.pin)

        shifts = bundle.shift_repo.list_all()
        for s in shifts:
            self.combo_shift.addItem(s.name, s.id)

    def _on_save(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        pin = self.combo_emp.currentData()
        shift_id = self.combo_shift.currentData()
        if not pin or shift_id is None:
            QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar colaborador y turno.")
            return

        py_from = self.date_from.date()
        v_from = date(py_from.year(), py_from.month(), py_from.day())
        try:
            assignment = EmployeeScheduleAssignment(
                id=None,
                employee_pin=pin,
                mode=AssignmentMode.FIXED,
                valid_from=v_from,
                shift_definition_id=shift_id,
            )
            bundle.schedule_assignment_repo.save(assignment)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al asignar", str(e))


class SchedulesView(QWidget):
    """Pantalla para administrar turnos de trabajo y asignaciones horarias."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._setup_ui()
        self.refresh_all()

        self.state.data_updated.connect(lambda k: self.refresh_all() if k in ("all", "schedules") else None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Turnos y Esquemas de Horario")
        title.setObjectName("h1Title")
        sub = QLabel("Configuración de jornadas fijas, nocturnas y asignaciones por empleado.")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_new_shift = QPushButton("+ Nuevo Turno")
        self.btn_new_shift.setObjectName("primaryBtn")
        self.btn_new_shift.clicked.connect(self._add_shift)
        top.addWidget(self.btn_new_shift)

        self.btn_new_assign = QPushButton("+ Asignar Horario")
        self.btn_new_assign.clicked.connect(self._add_assignment)
        top.addWidget(self.btn_new_assign)

        layout.addLayout(top)

        # Pestañas
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Turnos
        tab_shifts = QWidget()
        s_layout = QVBoxLayout(tab_shifts)
        self.shift_table = QTableWidget()
        self.shift_table.setColumnCount(6)
        self.shift_table.setHorizontalHeaderLabels([
            "ID", "Nombre de Turno", "Entrada", "Salida", "Tolerancia", "Nocturno"
        ])
        self.shift_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.shift_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shift_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        s_layout.addWidget(self.shift_table)
        self.tabs.addTab(tab_shifts, "Catálogo de Turnos")

        # Tab 2: Asignaciones
        tab_assign = QWidget()
        a_layout = QVBoxLayout(tab_assign)
        self.assign_table = QTableWidget()
        self.assign_table.setColumnCount(5)
        self.assign_table.setHorizontalHeaderLabels([
            "PIN Colaborador", "Modo", "Turno Asignado", "Vigente Desde", "Vigente Hasta"
        ])
        self.assign_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.assign_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.assign_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        a_layout.addWidget(self.assign_table)
        self.tabs.addTab(tab_assign, "Asignaciones Activas")

    def refresh_all(self) -> None:
        self.refresh_shifts()
        self.refresh_assignments()

    def refresh_shifts(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            shifts = bundle.shift_repo.list_all()
            self.shift_table.setRowCount(len(shifts))
            for row, s in enumerate(shifts):
                self.shift_table.setItem(row, 0, QTableWidgetItem(str(s.id)))
                self.shift_table.setItem(row, 1, QTableWidgetItem(s.name))
                self.shift_table.setItem(row, 2, QTableWidgetItem(s.start_time.strftime("%H:%M") if s.start_time else "-"))
                self.shift_table.setItem(row, 3, QTableWidgetItem(s.end_time.strftime("%H:%M") if s.end_time else "-"))
                self.shift_table.setItem(row, 4, QTableWidgetItem(f"{s.tolerance_minutes} min"))
                self.shift_table.setItem(row, 5, QTableWidgetItem("SÍ" if s.crosses_midnight else "NO"))
        except Exception:
            pass

    def refresh_assignments(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all()}
            assignments = bundle.schedule_assignment_repo.list_all() if hasattr(bundle.schedule_assignment_repo, "list_all") else []
            self.assign_table.setRowCount(len(assignments))
            for row, a in enumerate(assignments):
                self.assign_table.setItem(row, 0, QTableWidgetItem(str(a.employee_pin)))
                mode_str = a.mode.value if hasattr(a.mode, "value") else str(a.mode)
                self.assign_table.setItem(row, 1, QTableWidgetItem(mode_str))
                shift_name = shifts_map.get(a.shift_definition_id, "-")
                self.assign_table.setItem(row, 2, QTableWidgetItem(shift_name))
                self.assign_table.setItem(row, 3, QTableWidgetItem(str(a.valid_from)))
                self.assign_table.setItem(row, 4, QTableWidgetItem(str(a.valid_until or "Indefinido")))
        except Exception:
            pass

    def _add_shift(self) -> None:
        dialog = ShiftEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_shifts()
            self.state.data_updated.emit("schedules")
            self.state.notify("Turno registrado correctamente.", "success")

    def _add_assignment(self) -> None:
        dialog = AssignmentDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_assignments()
            self.state.data_updated.emit("schedules")
            self.state.notify("Horario asignado exitosamente.", "success")

"""Vista de Gestión de Turnos, Asignación de Horarios, Patrones Rotativos y Eventualidades."""

from datetime import date, time

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
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
from attendance.adapters.gui.views.schedule_dialog import SetEmployeeScheduleDialog
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import (
    AssignmentMode,
    RotationFrequency,
    ShiftCategory,
    Weekday,
)
from attendance.domain.schedule.exception import ScheduleException
from attendance.domain.schedule.rotation import RotationPattern
from attendance.domain.schedule.shift import ShiftDefinition

WEEKDAY_LABELS = [
    (Weekday.MONDAY, "Lun"),
    (Weekday.TUESDAY, "Mar"),
    (Weekday.WEDNESDAY, "Mié"),
    (Weekday.THURSDAY, "Jue"),
    (Weekday.FRIDAY, "Vie"),
    (Weekday.SATURDAY, "Sáb"),
    (Weekday.SUNDAY, "Dom"),
]


class ShiftEditDialog(QDialog):
    """Modal para registrar o editar un turno laboral."""

    def __init__(
        self,
        app_state: AppState,
        shift: ShiftDefinition | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.shift = shift
        self.setWindowTitle("Editar Turno de Trabajo" if shift else "Nuevo Turno de Trabajo")
        self.setMinimumWidth(460)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.txt_name = QLineEdit(self.shift.name if self.shift else "Matutino 08:00 - 16:00")

        self.combo_category = QComboBox()
        self.combo_category.addItem("Regular", ShiftCategory.REGULAR)
        self.combo_category.addItem("Matutino", ShiftCategory.MATUTINO)
        self.combo_category.addItem("Vespertino", ShiftCategory.VESPERTINO)
        self.combo_category.addItem("Nocturno", ShiftCategory.NOCTURNO)
        self.combo_category.addItem("Mixto", ShiftCategory.MIXTO)
        self.combo_category.addItem("Partido", ShiftCategory.PARTIDO)
        self.combo_category.addItem("Personalizado", ShiftCategory.PERSONALIZADO)

        if self.shift:
            for i in range(self.combo_category.count()):
                if self.combo_category.itemData(i) == self.shift.category:
                    self.combo_category.setCurrentIndex(i)
                    break

        self.time_start = QTimeEdit()
        st = self.shift.start_time if self.shift and self.shift.start_time else time(8, 0)
        self.time_start.setTime(QTime(st.hour, st.minute, st.second))

        self.time_end = QTimeEdit()
        et = self.shift.end_time if self.shift and self.shift.end_time else time(16, 0)
        self.time_end.setTime(QTime(et.hour, et.minute, et.second))

        self.spin_tolerance = QSpinBox()
        self.spin_tolerance.setRange(0, 180)
        self.spin_tolerance.setValue(self.shift.tolerance_minutes if self.shift else 10)
        self.spin_tolerance.setSuffix(" min")

        self.chk_midnight = QCheckBox("Cruza la medianoche (Jornada Nocturna)")
        self.chk_midnight.setChecked(self.shift.crosses_midnight if self.shift else False)

        form.addRow("Nombre del Turno (*):", self.txt_name)
        form.addRow("Categoría:", self.combo_category)
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
        category = self.combo_category.currentData()

        try:
            if self.shift:
                self.shift.name = name
                self.shift.category = category
                self.shift.start_time = start_t
                self.shift.end_time = end_t
                self.shift.tolerance_minutes = tol
                self.shift.crosses_midnight = midnight
                bundle.shift_repo.save(self.shift)
            else:
                shift = ShiftDefinition(
                    id=None,
                    name=name,
                    category=category,
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
    """Modal para asignar un turno fijo o rotativo con definición de días de descanso."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self.setWindowTitle("Asignar Horario a Colaborador")
        self.setMinimumWidth(520)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.combo_emp = QComboBox()
        self.combo_shift = QComboBox()
        self.combo_pattern = QComboBox()
        self._load_combos()

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Fijo (Semana Estándar)", AssignmentMode.FIXED)
        self.combo_mode.addItem("Rotativo (Ciclo Cíclico)", AssignmentMode.ROTATING)
        self.combo_mode.addItem("Abierto / Flexible", AssignmentMode.OPEN)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

        # Controles de días laborables y descanso (Modo Fijo)
        self.days_group = QGroupBox("Esquema Semanal de Descanso y Trabajo")
        d_layout = QVBoxLayout(self.days_group)

        self.combo_preset = QComboBox()
        self.combo_preset.addItem("Lunes a Sábado (Descanso: Domingo)", "mon_sat")
        self.combo_preset.addItem("Lunes a Viernes (Descanso: Sábado y Domingo)", "mon_fri")
        self.combo_preset.addItem("Todos los días (Sin descansos fijos)", "all")
        self.combo_preset.addItem("Personalizado...", "custom")
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        d_layout.addWidget(self.combo_preset)

        chk_layout = QHBoxLayout()
        self.day_checkboxes: dict[Weekday, QCheckBox] = {}
        for wday, lbl in WEEKDAY_LABELS:
            chk = QCheckBox(lbl)
            chk.setChecked(wday != Weekday.SUNDAY)
            chk.toggled.connect(self._on_day_toggled)
            self.day_checkboxes[wday] = chk
            chk_layout.addWidget(chk)
        d_layout.addLayout(chk_layout)

        self.lbl_rest_preview = QLabel("Descanso semanal: Domingo")
        self.lbl_rest_preview.setStyleSheet("color: #0284c7; font-weight: 500;")
        d_layout.addWidget(self.lbl_rest_preview)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        td = date.today()
        self.date_from.setDate(QDate(td.year, td.month, td.day))

        self.chk_indefinite = QCheckBox("Vigencia indefinida (sin fecha de término)")
        self.chk_indefinite.setChecked(True)
        self.date_until = QDateEdit()
        self.date_until.setCalendarPopup(True)
        self.date_until.setDate(QDate(td.year + 1, td.month, td.day))
        self.date_until.setEnabled(False)
        self.chk_indefinite.toggled.connect(lambda chk: self.date_until.setEnabled(not chk))

        form.addRow("Colaborador (*):", self.combo_emp)
        form.addRow("Modo de Jornada:", self.combo_mode)
        form.addRow("Turno Fijo (*):", self.combo_shift)
        form.addRow("Patrón Rotativo (*):", self.combo_pattern)
        form.addRow("", self.days_group)
        form.addRow("Vigente a partir de (*):", self.date_from)
        form.addRow("", self.chk_indefinite)
        form.addRow("Válido hasta:", self.date_until)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Asignar Horario")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        self._on_mode_changed()

    def _load_combos(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        employees = bundle.employee_repo.list_all()
        for e in employees:
            self.combo_emp.addItem(f"{e.pin} - {e.full_name}", e.pin)

        shifts = bundle.shift_repo.list_all()
        for s in shifts:
            st = s.start_time.strftime("%H:%M") if s.start_time else "--:--"
            et = s.end_time.strftime("%H:%M") if s.end_time else "--:--"
            self.combo_shift.addItem(f"{s.name} ({st} - {et})", s.id)

        patterns = bundle.rotation_pattern_repo.list_all()
        for p in patterns:
            work_c = sum(1 for sid in p.shift_sequence if sid is not None)
            rest_c = sum(1 for sid in p.shift_sequence if sid is None)
            self.combo_pattern.addItem(f"{p.name} ({work_c}T / {rest_c}D)", p.id)

    def _on_mode_changed(self) -> None:
        mode = self.combo_mode.currentData()
        is_fixed = mode == AssignmentMode.FIXED
        is_rotating = mode == AssignmentMode.ROTATING

        self.combo_shift.setVisible(is_fixed)
        self.combo_pattern.setVisible(is_rotating)
        self.days_group.setVisible(is_fixed)

    def _on_preset_changed(self) -> None:
        code = self.combo_preset.currentData()
        if code == "custom":
            return

        for wday, chk in self.day_checkboxes.items():
            chk.blockSignals(True)
            if code == "mon_sat":
                chk.setChecked(wday != Weekday.SUNDAY)
            elif code == "mon_fri":
                chk.setChecked(wday not in (Weekday.SATURDAY, Weekday.SUNDAY))
            elif code == "all":
                chk.setChecked(True)
            chk.blockSignals(False)

        self._update_rest_preview()

    def _on_day_toggled(self) -> None:
        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentIndex(3)  # Personalizado
        self.combo_preset.blockSignals(False)
        self._update_rest_preview()

    def _update_rest_preview(self) -> None:
        rest_days = [
            lbl for wday, lbl in WEEKDAY_LABELS if not self.day_checkboxes[wday].isChecked()
        ]
        if not rest_days:
            self.lbl_rest_preview.setText("Sin días de descanso fijos (labora todos los días)")
            self.lbl_rest_preview.setStyleSheet("color: #64748b; font-weight: 500;")
        else:
            self.lbl_rest_preview.setText(f"Descanso semanal: {', '.join(rest_days)}")
            self.lbl_rest_preview.setStyleSheet("color: #0284c7; font-weight: 500;")

    def _on_save(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        pin = self.combo_emp.currentData()
        mode = self.combo_mode.currentData()

        if not pin:
            QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar un colaborador.")
            return

        shift_id = None
        pattern_id = None

        if mode == AssignmentMode.FIXED:
            shift_id = self.combo_shift.currentData()
            if shift_id is None:
                QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar un turno fijo.")
                return
        elif mode == AssignmentMode.ROTATING:
            pattern_id = self.combo_pattern.currentData()
            if pattern_id is None:
                QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar un patrón de rotación.")
                return

        working_weekdays = None
        if mode == AssignmentMode.FIXED:
            working_weekdays = {
                wday for wday, chk in self.day_checkboxes.items() if chk.isChecked()
            }
            if not working_weekdays:
                QMessageBox.warning(
                    self, "Validación", "Debe marcar al menos un día laborable en la semana."
                )
                return

        py_from = self.date_from.date()
        v_from = date(py_from.year(), py_from.month(), py_from.day())

        v_until = None
        if not self.chk_indefinite.isChecked():
            py_until = self.date_until.date()
            v_until = date(py_until.year(), py_until.month(), py_until.day())
            if v_until < v_from:
                QMessageBox.warning(
                    self, "Fecha inválida", "La fecha de fin no puede ser anterior a la de inicio."
                )
                return

        try:
            assignment = EmployeeScheduleAssignment(
                id=None,
                employee_pin=pin,
                mode=mode,
                valid_from=v_from,
                valid_until=v_until,
                working_weekdays=working_weekdays,
                shift_definition_id=shift_id,
                rotation_pattern_id=pattern_id,
            )
            bundle.schedule_assignment_repo.save(assignment)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al asignar", str(e))


class RotationPatternDialog(QDialog):
    """Modal para registrar un nuevo patrón de rotación cíclico (6x1, 5x2, 24x48, etc.)."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self.setWindowTitle("Nuevo Patrón de Rotación")
        self.setMinimumWidth(500)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.txt_name = QLineEdit("Patrón 6x1 Matutino")

        self.txt_sequence = QLineEdit("1, 1, 1, 1, 1, 1, OFF")
        self.txt_sequence.setPlaceholderText("Ej. 1, 1, 1, 1, 1, 1, OFF o 1, OFF, 2, OFF")

        lbl_help = QLabel(
            "Indique los IDs de los turnos separados por coma.\n"
            "Use 'OFF' o 'REST' para los días de descanso dentro del ciclo."
        )
        lbl_help.setObjectName("mutedLabel")

        self.combo_freq = QComboBox()
        self.combo_freq.addItem("Diaria (Cada paso es 1 día)", RotationFrequency.DAILY)
        self.combo_freq.addItem("Semanal (Cada paso es 1 semana)", RotationFrequency.WEEKLY)
        self.combo_freq.addItem("Quincenal (Cada paso son 2 semanas)", RotationFrequency.BIWEEKLY)
        self.combo_freq.addItem("Mensual (Cada paso es 1 mes)", RotationFrequency.MONTHLY)

        self.date_anchor = QDateEdit()
        self.date_anchor.setCalendarPopup(True)
        td = date.today()
        self.date_anchor.setDate(QDate(td.year, td.month, td.day))

        form.addRow("Nombre del Patrón (*):", self.txt_name)
        form.addRow("Secuencia de Turnos (*):", self.txt_sequence)
        form.addRow("", lbl_help)
        form.addRow("Frecuencia de Rotación:", self.combo_freq)
        form.addRow("Fecha Ancla de Inicio:", self.date_anchor)
        layout.addLayout(form)

        # Referencia de turnos disponibles
        if self.state.bundle:
            shifts = self.state.bundle.shift_repo.list_all()
            if shifts:
                ref_box = QGroupBox("Guía de Turnos Registrados")
                ref_layout = QVBoxLayout(ref_box)
                ref_text = ", ".join(f"ID {s.id}: {s.name}" for s in shifts if s.id is not None)
                ref_lbl = QLabel(ref_text)
                ref_lbl.setWordWrap(True)
                ref_layout.addWidget(ref_lbl)
                layout.addWidget(ref_box)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar Patrón")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        seq_str = self.txt_sequence.text().strip()

        if not name or not seq_str:
            QMessageBox.warning(self, "Campos requeridos", "El nombre y la secuencia son obligatorios.")
            return

        items = [s.strip().upper() for s in seq_str.split(",") if s.strip()]
        sequence: list[int | None] = []
        for it in items:
            if it in ("OFF", "REST", "NONE", "DESCANSO", "LIBRE", "-"):
                sequence.append(None)
            else:
                try:
                    sequence.append(int(it))
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Secuencia inválida",
                        f"'{it}' no es un ID numérico ni 'OFF' para descanso.",
                    )
                    return

        if not sequence:
            QMessageBox.warning(self, "Secuencia vacía", "Debe ingresar al menos un elemento en la secuencia.")
            return

        py_anchor = self.date_anchor.date()
        anchor = date(py_anchor.year(), py_anchor.month(), py_anchor.day())
        freq = self.combo_freq.currentData()

        try:
            pattern = RotationPattern(
                id=None,
                name=name,
                shift_sequence=sequence,
                frequency=freq,
                anchor_date=anchor,
            )
            if self.state.bundle:
                self.state.bundle.rotation_pattern_repo.save(pattern)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar patrón", str(e))


class ScheduleExceptionDialog(QDialog):
    """Modal para registrar una eventualidad o excepción puntual de horario."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self.setWindowTitle("Registrar Eventualidad de Horario")
        self.setMinimumWidth(480)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.combo_emp = QComboBox()
        self.combo_shift = QComboBox()
        self._load_combos()

        self.date_target = QDateEdit()
        self.date_target.setCalendarPopup(True)
        td = date.today()
        self.date_target.setDate(QDate(td.year, td.month, td.day))

        self.combo_type = QComboBox()
        self.combo_type.addItem("Día de Descanso Extraordinario (Forzar OFF / Libre)", "rest")
        self.combo_type.addItem("Turno Extraordinario (Cambio puntual de turno)", "shift")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)

        self.txt_reason = QLineEdit("Cambio de día de descanso acordado")
        self.txt_reason.setPlaceholderText("Motivo del cambio...")

        form.addRow("Colaborador (*):", self.combo_emp)
        form.addRow("Fecha de la Eventualidad (*):", self.date_target)
        form.addRow("Efecto / Tipo (*):", self.combo_type)
        form.addRow("Turno a Aplicar:", self.combo_shift)
        form.addRow("Motivo / Justificación:", self.txt_reason)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Registrar Eventualidad")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        self._on_type_changed()

    def _load_combos(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        for e in bundle.employee_repo.list_all():
            self.combo_emp.addItem(f"{e.pin} - {e.full_name}", e.pin)

        for s in bundle.shift_repo.list_all():
            self.combo_shift.addItem(f"{s.name} (ID {s.id})", s.id)

    def _on_type_changed(self) -> None:
        is_shift = self.combo_type.currentData() == "shift"
        self.combo_shift.setVisible(is_shift)

    def _on_save(self) -> None:
        bundle = self.state.bundle
        if not bundle or not bundle.schedule_exception_repo:
            QMessageBox.critical(self, "Error", "Repositorio de excepciones no disponible.")
            return

        pin = self.combo_emp.currentData()
        if not pin:
            QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar un colaborador.")
            return

        py_date = self.date_target.date()
        target_d = date(py_date.year(), py_date.month(), py_date.day())

        shift_id = None
        if self.combo_type.currentData() == "shift":
            shift_id = self.combo_shift.currentData()
            if shift_id is None:
                QMessageBox.warning(self, "Campos requeridos", "Debe seleccionar el turno a forzar.")
                return

        reason = self.txt_reason.text().strip() or "Eventualidad de horario"

        try:
            exc = ScheduleException(
                id=None,
                employee_pin=pin,
                date=target_d,
                shift_definition_id=shift_id,
                reason=reason,
            )
            bundle.schedule_exception_repo.save(exc)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al registrar", str(e))


class SchedulesView(QWidget):
    """Pantalla para administrar turnos de trabajo, descansos fijos/rotativos y eventualidades."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._setup_ui()
        self.refresh_all()

        self.state.data_updated.connect(
            lambda k: self.refresh_all() if k in ("all", "schedules") else None
        )

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado con botones de acción
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Turnos, Descansos y Esquemas de Horario")
        title.setObjectName("h1Title")
        sub = QLabel(
            "Configuración de jornadas fijas, descansos semanales, rotaciones cíclicas y eventualidades puntuales."
        )
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_set_schedule = QPushButton("🗓️ Establecer Horario")
        self.btn_set_schedule.setObjectName("primaryBtn")
        self.btn_set_schedule.clicked.connect(lambda: self._open_set_schedule_dialog())
        top.addWidget(self.btn_set_schedule)

        self.btn_new_shift = QPushButton("+ Nuevo Turno")
        self.btn_new_shift.clicked.connect(self._add_shift)
        top.addWidget(self.btn_new_shift)

        self.btn_new_exception = QPushButton("⚡ Eventualidad")
        self.btn_new_exception.clicked.connect(self._add_exception)
        top.addWidget(self.btn_new_exception)

        layout.addLayout(top)

        # Pestañas
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Catálogo de Turnos
        tab_shifts = QWidget()
        s_layout = QVBoxLayout(tab_shifts)
        s_layout.setSpacing(12)

        s_bar = QHBoxLayout()
        self.btn_edit_shift = QPushButton("✏️ Editar Turno")
        self.btn_edit_shift.clicked.connect(self._edit_shift)
        self.btn_delete_shift = QPushButton("🗑️ Eliminar Turno")
        self.btn_delete_shift.clicked.connect(self._delete_shift)
        s_bar.addWidget(self.btn_edit_shift)
        s_bar.addWidget(self.btn_delete_shift)
        s_bar.addStretch()
        s_layout.addLayout(s_bar)

        self.shift_table = QTableWidget()
        self.shift_table.setColumnCount(7)
        self.shift_table.setHorizontalHeaderLabels([
            "ID", "Nombre de Turno", "Categoría", "Entrada", "Salida", "Tolerancia", "Cruza Medianoche"
        ])
        self.shift_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.shift_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shift_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        s_layout.addWidget(self.shift_table)
        self.tabs.addTab(tab_shifts, "Catálogo de Turnos")

        # Tab 2: Asignaciones de Horario
        tab_assign = QWidget()
        a_layout = QVBoxLayout(tab_assign)
        a_layout.setSpacing(12)

        a_bar = QHBoxLayout()
        self.txt_filter_assign = QLineEdit()
        self.txt_filter_assign.setPlaceholderText("Filtrar asignaciones por PIN o nombre...")
        self.txt_filter_assign.textChanged.connect(self.refresh_assignments)
        a_bar.addWidget(self.txt_filter_assign)

        self.btn_set_sched_tab = QPushButton("🗓️ Establecer Horario")
        self.btn_set_sched_tab.setObjectName("primaryBtn")
        self.btn_set_sched_tab.clicked.connect(lambda: self._open_set_schedule_dialog())
        a_bar.addWidget(self.btn_set_sched_tab)

        self.btn_delete_assign = QPushButton("🗑️ Eliminar Asignación")
        self.btn_delete_assign.clicked.connect(self._delete_assignment)
        a_bar.addWidget(self.btn_delete_assign)
        a_layout.addLayout(a_bar)

        self.assign_table = QTableWidget()
        self.assign_table.setColumnCount(8)
        self.assign_table.setHorizontalHeaderLabels([
            "ID", "PIN", "Colaborador", "Turno / Patrón", "Modo", "Esquema Descanso", "Desde", "Hasta"
        ])
        self.assign_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.assign_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.assign_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        a_layout.addWidget(self.assign_table)
        self.tabs.addTab(tab_assign, "Asignaciones de Horario")

        # Tab 3: Patrones de Rotación
        tab_patterns = QWidget()
        p_layout = QVBoxLayout(tab_patterns)
        p_layout.setSpacing(12)

        p_bar = QHBoxLayout()
        self.btn_delete_pattern = QPushButton("🗑️ Eliminar Patrón")
        self.btn_delete_pattern.clicked.connect(self._delete_pattern)
        p_bar.addWidget(self.btn_delete_pattern)
        p_bar.addStretch()
        p_layout.addLayout(p_bar)

        self.pattern_table = QTableWidget()
        self.pattern_table.setColumnCount(6)
        self.pattern_table.setHorizontalHeaderLabels([
            "ID", "Nombre del Patrón", "Duración Ciclo", "Secuencia Resumida", "Frecuencia", "Fecha Ancla"
        ])
        self.pattern_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pattern_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pattern_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        p_layout.addWidget(self.pattern_table)
        self.tabs.addTab(tab_patterns, "Patrones de Rotación")

        # Tab 4: Excepciones y Eventualidades
        tab_exceptions = QWidget()
        e_layout = QVBoxLayout(tab_exceptions)
        e_layout.setSpacing(12)

        e_bar = QHBoxLayout()
        self.txt_filter_exc = QLineEdit()
        self.txt_filter_exc.setPlaceholderText("Filtrar eventualidades por PIN...")
        self.txt_filter_exc.textChanged.connect(self.refresh_exceptions)
        e_bar.addWidget(self.txt_filter_exc)

        self.btn_delete_exc = QPushButton("🗑️ Revocar Eventualidad")
        self.btn_delete_exc.clicked.connect(self._delete_exception)
        e_bar.addWidget(self.btn_delete_exc)
        e_layout.addLayout(e_bar)

        self.exc_table = QTableWidget()
        self.exc_table.setColumnCount(6)
        self.exc_table.setHorizontalHeaderLabels([
            "ID", "PIN", "Colaborador", "Fecha", "Efecto / Turno", "Motivo"
        ])
        self.exc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.exc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.exc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        e_layout.addWidget(self.exc_table)
        self.tabs.addTab(tab_exceptions, "Excepciones y Eventualidades")

    def refresh_all(self) -> None:
        self.refresh_shifts()
        self.refresh_assignments()
        self.refresh_rotation_patterns()
        self.refresh_exceptions()

    def refresh_shifts(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            shifts = bundle.shift_repo.list_all()
            self.shift_table.setRowCount(len(shifts))
            for row, s in enumerate(shifts):
                self.shift_table.setItem(row, 0, QTableWidgetItem(str(s.id or "-")))
                self.shift_table.setItem(row, 1, QTableWidgetItem(s.name))
                cat_str = s.category.value.upper() if hasattr(s.category, "value") else str(s.category)
                self.shift_table.setItem(row, 2, QTableWidgetItem(cat_str))
                self.shift_table.setItem(row, 3, QTableWidgetItem(s.start_time.strftime("%H:%M") if s.start_time else "-"))
                self.shift_table.setItem(row, 4, QTableWidgetItem(s.end_time.strftime("%H:%M") if s.end_time else "-"))
                self.shift_table.setItem(row, 5, QTableWidgetItem(f"{s.tolerance_minutes} min"))
                self.shift_table.setItem(row, 6, QTableWidgetItem("SÍ" if s.crosses_midnight else "NO"))
        except Exception:
            pass

    def refresh_assignments(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all() if s.id is not None}
            patterns_map = {p.id: p.name for p in bundle.rotation_pattern_repo.list_all() if p.id is not None}
            emp_map = {e.pin: e.full_name for e in bundle.employee_repo.list_all()}
            assignments = (
                bundle.schedule_assignment_repo.list_all()
                if hasattr(bundle.schedule_assignment_repo, "list_all")
                else []
            )

            query = self.txt_filter_assign.text().strip().lower()
            if query:
                assignments = [
                    a
                    for a in assignments
                    if query in str(a.employee_pin).lower()
                    or query in emp_map.get(a.employee_pin, "").lower()
                ]

            self.assign_table.setRowCount(len(assignments))
            for row, a in enumerate(assignments):
                self.assign_table.setItem(row, 0, QTableWidgetItem(str(a.id or "-")))
                self.assign_table.setItem(row, 1, QTableWidgetItem(str(a.employee_pin)))
                self.assign_table.setItem(row, 2, QTableWidgetItem(emp_map.get(a.employee_pin, "Desconocido")))

                if a.mode == AssignmentMode.FIXED:
                    detail = shifts_map.get(a.shift_definition_id, f"Turno #{a.shift_definition_id}") if a.shift_definition_id is not None else "-"
                elif a.mode == AssignmentMode.ROTATING:
                    detail = patterns_map.get(a.rotation_pattern_id, f"Patrón #{a.rotation_pattern_id}") if a.rotation_pattern_id is not None else "-"
                else:
                    detail = "Horario Flexible"

                self.assign_table.setItem(row, 3, QTableWidgetItem(detail))
                mode_str = a.mode.value if hasattr(a.mode, "value") else str(a.mode)
                self.assign_table.setItem(row, 4, QTableWidgetItem(mode_str.upper()))

                # Resumen de descansos
                if a.working_weekdays is not None:
                    rest_names = [
                        lbl for wday, lbl in WEEKDAY_LABELS if wday not in a.working_weekdays
                    ]
                    rest_str = f"Descanso: {', '.join(rest_names)}" if rest_names else "Todos los días"
                else:
                    rest_str = "Rotativo según ciclo" if a.mode == AssignmentMode.ROTATING else "Semana estándar"

                self.assign_table.setItem(row, 5, QTableWidgetItem(rest_str))
                self.assign_table.setItem(row, 6, QTableWidgetItem(str(a.valid_from)))
                self.assign_table.setItem(row, 7, QTableWidgetItem(str(a.valid_until or "Indefinido")))
        except Exception:
            pass

    def refresh_rotation_patterns(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            patterns = bundle.rotation_pattern_repo.list_all()
            self.pattern_table.setRowCount(len(patterns))
            for row, p in enumerate(patterns):
                self.pattern_table.setItem(row, 0, QTableWidgetItem(str(p.id or "-")))
                self.pattern_table.setItem(row, 1, QTableWidgetItem(p.name))
                self.pattern_table.setItem(row, 2, QTableWidgetItem(f"{len(p.shift_sequence)} períodos"))
                work_c = sum(1 for sid in p.shift_sequence if sid is not None)
                rest_c = sum(1 for sid in p.shift_sequence if sid is None)
                self.pattern_table.setItem(row, 3, QTableWidgetItem(f"{work_c} Trab. / {rest_c} Desc."))
                self.pattern_table.setItem(row, 4, QTableWidgetItem(p.frequency.value.upper()))
                self.pattern_table.setItem(row, 5, QTableWidgetItem(str(p.anchor_date)))
        except Exception:
            pass

    def refresh_exceptions(self) -> None:
        bundle = self.state.bundle
        if not bundle or not bundle.schedule_exception_repo:
            return
        try:
            shifts_map = {s.id: s.name for s in bundle.shift_repo.list_all() if s.id is not None}
            emp_map = {e.pin: e.full_name for e in bundle.employee_repo.list_all()}
            exceptions = bundle.schedule_exception_repo.list_all()

            query = self.txt_filter_exc.text().strip().lower()
            if query:
                exceptions = [
                    e
                    for e in exceptions
                    if query in str(e.employee_pin).lower()
                    or query in emp_map.get(e.employee_pin, "").lower()
                ]

            self.exc_table.setRowCount(len(exceptions))
            for row, exc in enumerate(exceptions):
                self.exc_table.setItem(row, 0, QTableWidgetItem(str(exc.id or "-")))
                self.exc_table.setItem(row, 1, QTableWidgetItem(str(exc.employee_pin)))
                self.exc_table.setItem(row, 2, QTableWidgetItem(emp_map.get(exc.employee_pin, "-")))
                self.exc_table.setItem(row, 3, QTableWidgetItem(str(exc.date)))

                if exc.shift_definition_id is None:
                    efecto = "DESCANSO FORZADO (OFF)"
                else:
                    s_name = shifts_map.get(exc.shift_definition_id, f"Turno #{exc.shift_definition_id}")
                    efecto = f"Turno: {s_name}"
                self.exc_table.setItem(row, 4, QTableWidgetItem(efecto))
                self.exc_table.setItem(row, 5, QTableWidgetItem(exc.reason or "-"))
        except Exception:
            pass

    def _get_selected_shift(self) -> ShiftDefinition | None:
        row = self.shift_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un turno de la tabla.")
            return None
        id_item = self.shift_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle:
            return None
        return self.state.bundle.shift_repo.get_by_id(int(id_item.text()))

    def _add_shift(self) -> None:
        dialog = ShiftEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_shifts()
            self.state.data_updated.emit("schedules")
            self.state.notify("Turno registrado correctamente.", "success")

    def _edit_shift(self) -> None:
        shift = self._get_selected_shift()
        if not shift:
            return
        dialog = ShiftEditDialog(self.state, shift=shift, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_shifts()
            self.state.data_updated.emit("schedules")
            self.state.notify("Turno actualizado.", "success")

    def _delete_shift(self) -> None:
        shift = self._get_selected_shift()
        if not shift or not shift.id or not self.state.bundle:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el turno '{shift.name}' (ID: {shift.id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.shift_repo.delete(shift.id)
            if success:
                self.refresh_shifts()
                self.state.data_updated.emit("schedules")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el turno.")

    def _open_set_schedule_dialog(self, preset_pin: str | None = None) -> None:
        if not preset_pin:
            row = self.assign_table.currentRow()
            if row >= 0:
                pin_item = self.assign_table.item(row, 1)
                if pin_item and pin_item.text():
                    preset_pin = pin_item.text().strip()

        dialog = SetEmployeeScheduleDialog(self.state, preset_employee_pin=preset_pin, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_assignments()
            self.refresh_patterns()
            self.state.data_updated.emit("schedules")

    def _add_assignment(self) -> None:
        dialog = AssignmentDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_assignments()
            self.state.data_updated.emit("schedules")
            self.state.notify("Horario asignado exitosamente.", "success")

    def _delete_assignment(self) -> None:
        row = self.assign_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione una asignación de la lista.")
            return
        id_item = self.assign_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle:
            return
        assign_id = int(id_item.text())

        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Desea eliminar la asignación de horario #{assign_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.schedule_assignment_repo.delete(assign_id)
            if success:
                self.refresh_assignments()
                self.state.data_updated.emit("schedules")
                self.state.notify(f"Asignación #{assign_id} eliminada.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar la asignación.")

    def _add_pattern(self) -> None:
        dialog = RotationPatternDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_rotation_patterns()
            self.state.data_updated.emit("schedules")
            self.state.notify("Patrón de rotación registrado.", "success")

    def _delete_pattern(self) -> None:
        row = self.pattern_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione un patrón de la lista.")
            return
        id_item = self.pattern_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle:
            return
        pattern_id = int(id_item.text())

        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Desea eliminar el patrón de rotación #{pattern_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.rotation_pattern_repo.delete(pattern_id)
            if success:
                self.refresh_rotation_patterns()
                self.state.data_updated.emit("schedules")
                self.state.notify(f"Patrón #{pattern_id} eliminado.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el patrón.")

    def _add_exception(self) -> None:
        dialog = ScheduleExceptionDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_exceptions()
            self.state.data_updated.emit("schedules")
            self.state.notify("Eventualidad de horario registrada.", "success")

    def _delete_exception(self) -> None:
        row = self.exc_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione una eventualidad de la lista.")
            return
        id_item = self.exc_table.item(row, 0)
        if not id_item or not id_item.text() or not self.state.bundle or not self.state.bundle.schedule_exception_repo:
            return
        exc_id = int(id_item.text())

        confirm = QMessageBox.question(
            self,
            "Confirmar Revocación",
            f"¿Desea revocar o eliminar la eventualidad #{exc_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.schedule_exception_repo.delete(exc_id)
            if success:
                self.refresh_exceptions()
                self.state.data_updated.emit("schedules")
                self.state.notify(f"Eventualidad #{exc_id} eliminada.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar la eventualidad.")

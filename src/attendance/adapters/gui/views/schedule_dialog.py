"""Diálogo interactivo para establecer horarios y descansos de empleados.

Permite configurar turnos fijos o rotativos, descansos fijos o rotativos
(escalonados/rolados, alternados, o ciclos NxM), con previsualización
interactiva en tiempo real para los próximos 30 días.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.application.schedule.plan_builder import (
    RestModeOption,
    SchedulePlanBuilder,
    SchedulePlanConfig,
    ShiftModeOption,
)
from attendance.domain.common.exceptions import ValidationError
from attendance.domain.organization.employee import Employee
from attendance.domain.schedule.shift import ShiftDefinition


class SetEmployeeScheduleDialog(QDialog):
    """Diálogo integral guiado para establecer horario y descansos."""

    def __init__(
        self,
        app_state: AppState,
        preset_employee_pin: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.preset_pin = preset_employee_pin
        self.setWindowTitle("🗓️ Establecer Horario y Descansos del Colaborador")
        self.resize(1060, 720)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(Theme.get_stylesheet())

        self.shifts_map: dict[int, ShiftDefinition] = {}
        self.employees_list: list[Employee] = []

        self._load_catalogs()
        self._setup_ui()
        self.update_preview()

    def _load_catalogs(self) -> None:
        bundle = self.state.bundle
        if bundle:
            all_shifts = bundle.shift_repo.list_all()
            self.shifts_map = {s.id: s for s in all_shifts if s.id is not None}
            self.employees_list = bundle.employee_repo.list_all()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Encabezado
        head = QVBoxLayout()
        title = QLabel("Configurar Horario y Días de Descanso")
        title.setObjectName("h2Title")
        sub = QLabel("Define el esquema de turnos y descansos (fijos o rotativos) con previsualización en vivo.")
        sub.setObjectName("mutedLabel")
        head.addWidget(title)
        head.addWidget(sub)
        main_layout.addLayout(head)

        # Divisor principal izquierda / derecha
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ====================================================================
        # PANEL IZQUIERDO: CONTROLES
        # ====================================================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(14)

        # 1. Colaborador y Fechas
        gb_emp = QGroupBox("1. Colaborador y Vigencia")
        emp_form = QFormLayout(gb_emp)
        emp_form.setSpacing(10)

        self.cb_employee = QComboBox()
        for emp in self.employees_list:
            self.cb_employee.addItem(f"{emp.full_name} ({emp.pin})", emp.pin)

        if self.preset_pin:
            idx = self.cb_employee.findData(self.preset_pin)
            if idx >= 0:
                self.cb_employee.setCurrentIndex(idx)

        self.cb_employee.currentIndexChanged.connect(self.update_preview)
        emp_form.addRow("Colaborador:", self.cb_employee)

        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate.currentDate())
        self.dt_from.dateChanged.connect(self.update_preview)
        emp_form.addRow("Válido Desde:", self.dt_from)

        until_row = QHBoxLayout()
        self.chk_indefinite = QCheckBox("Vigencia Indefinida")
        self.chk_indefinite.setChecked(True)
        self.dt_until = QDateEdit()
        self.dt_until.setCalendarPopup(True)
        self.dt_until.setDate(QDate.currentDate().addMonths(6))
        self.dt_until.setEnabled(False)
        self.dt_until.dateChanged.connect(self.update_preview)

        self.chk_indefinite.toggled.connect(
            lambda checked: self.dt_until.setEnabled(not checked)
        )
        self.chk_indefinite.toggled.connect(self.update_preview)

        until_row.addWidget(self.chk_indefinite)
        until_row.addWidget(self.dt_until)
        emp_form.addRow("Válido Hasta:", until_row)

        left_layout.addWidget(gb_emp)

        # 2. Esquema de Horario
        gb_shift = QGroupBox("2. Esquema de Horario de Trabajo")
        shift_vbox = QVBoxLayout(gb_shift)
        shift_vbox.setSpacing(10)

        shift_mode_row = QHBoxLayout()
        self.rb_shift_fixed = QRadioButton("Turno Fijo")
        self.rb_shift_rotating = QRadioButton("Turno Rotativo")
        self.rb_shift_fixed.setChecked(True)

        self.shift_group = QButtonGroup(self)
        self.shift_group.addButton(self.rb_shift_fixed)
        self.shift_group.addButton(self.rb_shift_rotating)

        shift_mode_row.addWidget(self.rb_shift_fixed)
        shift_mode_row.addWidget(self.rb_shift_rotating)
        shift_mode_row.addStretch()
        shift_vbox.addLayout(shift_mode_row)

        # Contenedor Turno Fijo
        self.widget_fixed_shift = QWidget()
        fs_layout = QFormLayout(self.widget_fixed_shift)
        fs_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_fixed_shift = QComboBox()
        for sid, s in self.shifts_map.items():
            self.cb_fixed_shift.addItem(
                f"{s.name} ({s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')})",
                sid,
            )
        self.cb_fixed_shift.currentIndexChanged.connect(self.update_preview)
        fs_layout.addRow("Turno asignado:", self.cb_fixed_shift)
        shift_vbox.addWidget(self.widget_fixed_shift)

        # Contenedor Turno Rotativo
        self.widget_rotating_shift = QWidget()
        rs_layout = QVBoxLayout(self.widget_rotating_shift)
        rs_layout.setContentsMargins(0, 0, 0, 0)
        rs_layout.setSpacing(6)

        rs_form = QFormLayout()
        self.cb_shift_freq = QComboBox()
        self.cb_shift_freq.addItem("Cada semana (7 días)", 1)
        self.cb_shift_freq.addItem("Cada 2 semanas / Quincenal", 2)
        self.cb_shift_freq.addItem("Cada 4 semanas / Mensual", 4)
        self.cb_shift_freq.currentIndexChanged.connect(self.update_preview)
        rs_form.addRow("Cambiar de turno:", self.cb_shift_freq)
        rs_layout.addLayout(rs_form)

        rs_layout.addWidget(QLabel("Secuencia ordenada de turnos a rotar:"))
        self.list_rot_shifts = QListWidget()
        self.list_rot_shifts.setMaximumHeight(90)
        rs_layout.addWidget(self.list_rot_shifts)

        btn_shifts_bar = QHBoxLayout()
        self.cb_add_shift = QComboBox()
        for sid, s in self.shifts_map.items():
            self.cb_add_shift.addItem(f"{s.name}", sid)
        btn_shifts_bar.addWidget(self.cb_add_shift)

        self.btn_add_shift = QPushButton("➕ Agregar")
        self.btn_add_shift.clicked.connect(self._add_rotating_shift_item)
        btn_shifts_bar.addWidget(self.btn_add_shift)

        self.btn_rem_shift = QPushButton("🗑️ Quitar")
        self.btn_rem_shift.clicked.connect(self._rem_rotating_shift_item)
        btn_shifts_bar.addWidget(self.btn_rem_shift)
        rs_layout.addLayout(btn_shifts_bar)

        # Cargar los primeros 2 turnos por defecto si existen
        shift_ids_list = list(self.shifts_map.keys())
        if len(shift_ids_list) >= 1:
            self._add_shift_to_list(shift_ids_list[0])
        if len(shift_ids_list) >= 2:
            self._add_shift_to_list(shift_ids_list[1])

        self.widget_rotating_shift.setVisible(False)
        shift_vbox.addWidget(self.widget_rotating_shift)

        self.rb_shift_fixed.toggled.connect(self._on_shift_mode_changed)
        left_layout.addWidget(gb_shift)

        # 3. Esquema de Días de Descanso
        gb_rest = QGroupBox("3. Esquema de Días de Descanso")
        rest_vbox = QVBoxLayout(gb_rest)
        rest_vbox.setSpacing(10)

        rest_mode_row = QHBoxLayout()
        self.rb_rest_fixed = QRadioButton("Descanso Fijo")
        self.rb_rest_rotating = QRadioButton("Descanso Rotativo")
        self.rb_rest_fixed.setChecked(True)

        self.rest_group = QButtonGroup(self)
        self.rest_group.addButton(self.rb_rest_fixed)
        self.rest_group.addButton(self.rb_rest_rotating)

        rest_mode_row.addWidget(self.rb_rest_fixed)
        rest_mode_row.addWidget(self.rb_rest_rotating)
        rest_mode_row.addStretch()
        rest_vbox.addLayout(rest_mode_row)

        # Contenedor Descanso Fijo
        self.widget_fixed_rest = QWidget()
        fr_layout = QVBoxLayout(self.widget_fixed_rest)
        fr_layout.setContentsMargins(0, 0, 0, 0)
        fr_layout.setSpacing(8)

        preset_bar = QHBoxLayout()
        self.btn_preset_sun = QPushButton("Solo Domingos")
        self.btn_preset_sun.clicked.connect(lambda: self._set_rest_presets([6]))
        self.btn_preset_sat_sun = QPushButton("Sáb y Dom")
        self.btn_preset_sat_sun.clicked.connect(lambda: self._set_rest_presets([5, 6]))
        self.btn_preset_none = QPushButton("Sin descansos fijos")
        self.btn_preset_none.clicked.connect(lambda: self._set_rest_presets([]))
        preset_bar.addWidget(self.btn_preset_sun)
        preset_bar.addWidget(self.btn_preset_sat_sun)
        preset_bar.addWidget(self.btn_preset_none)
        fr_layout.addLayout(preset_bar)

        days_box = QHBoxLayout()
        self.chk_days: list[QCheckBox] = []
        labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for idx, lbl in enumerate(labels):
            chk = QCheckBox(lbl)
            if idx == 6:  # Domingo por defecto descanso
                chk.setChecked(True)
            chk.toggled.connect(self.update_preview)
            self.chk_days.append(chk)
            days_box.addWidget(chk)
        fr_layout.addLayout(days_box)
        rest_vbox.addWidget(self.widget_fixed_rest)

        # Contenedor Descanso Rotativo
        self.widget_rotating_rest = QWidget()
        rr_layout = QVBoxLayout(self.widget_rotating_rest)
        rr_layout.setContentsMargins(0, 0, 0, 0)
        rr_layout.setSpacing(8)

        rr_form = QFormLayout()
        self.cb_rot_type = QComboBox()
        self.cb_rot_type.addItem("Se recorre al siguiente día (Rolado continuo)", "rolling")
        self.cb_rot_type.addItem("Días fijos de cambio (Alternado)", "alternating")
        self.cb_rot_type.addItem("Ciclo continuo Trabajo x Descanso (NxM)", "cycle")
        self.cb_rot_type.currentIndexChanged.connect(self._on_rot_type_changed)
        rr_form.addRow("¿Cómo cambia el descanso?", self.cb_rot_type)
        rr_layout.addLayout(rr_form)

        # Sub-panel A: Se recorre al siguiente día
        self.panel_rolling = QWidget()
        rol_layout = QFormLayout(self.panel_rolling)
        rol_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_roll_start = QComboBox()
        for idx, lbl in enumerate(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]):
            self.cb_roll_start.addItem(lbl, idx)
        self.cb_roll_start.setCurrentIndex(6)  # Domingo
        self.cb_roll_start.currentIndexChanged.connect(self.update_preview)
        rol_layout.addRow("Empieza descansando en:", self.cb_roll_start)

        self.cb_roll_freq = QComboBox()
        self.cb_roll_freq.addItem("Cada semana (+1 día)", 1)
        self.cb_roll_freq.addItem("Cada 2 semanas / Quincenal", 2)
        self.cb_roll_freq.addItem("Cada 4 semanas / Mensual", 4)
        self.cb_roll_freq.currentIndexChanged.connect(self.update_preview)
        rol_layout.addRow("Se recorre cada:", self.cb_roll_freq)
        rr_layout.addWidget(self.panel_rolling)

        # Sub-panel B: Alternado entre días fijos
        self.panel_alt = QWidget()
        alt_layout = QFormLayout(self.panel_alt)
        alt_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_alt_day1 = QComboBox()
        self.cb_alt_day2 = QComboBox()
        for idx, lbl in enumerate(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]):
            self.cb_alt_day1.addItem(lbl, idx)
            self.cb_alt_day2.addItem(lbl, idx)
        self.cb_alt_day1.setCurrentIndex(6)  # Domingo
        self.cb_alt_day2.setCurrentIndex(5)  # Sábado
        self.cb_alt_day1.currentIndexChanged.connect(self.update_preview)
        self.cb_alt_day2.currentIndexChanged.connect(self.update_preview)
        alt_layout.addRow("Descanso Semana A:", self.cb_alt_day1)
        alt_layout.addRow("Descanso Semana B:", self.cb_alt_day2)

        self.cb_alt_freq = QComboBox()
        self.cb_alt_freq.addItem("Alternar cada semana", 1)
        self.cb_alt_freq.addItem("Alternar cada 2 semanas", 2)
        self.cb_alt_freq.currentIndexChanged.connect(self.update_preview)
        alt_layout.addRow("Frecuencia alternancia:", self.cb_alt_freq)
        self.panel_alt.setVisible(False)
        rr_layout.addWidget(self.panel_alt)

        # Sub-panel C: Ciclo continuo NxM
        self.panel_cycle = QWidget()
        cyc_layout = QFormLayout(self.panel_cycle)
        cyc_layout.setContentsMargins(0, 0, 0, 0)
        self.sp_work_days = QSpinBox()
        self.sp_work_days.setRange(1, 30)
        self.sp_work_days.setValue(6)
        self.sp_work_days.valueChanged.connect(self.update_preview)
        cyc_layout.addRow("Días de trabajo continuo:", self.sp_work_days)

        self.sp_rest_days = QSpinBox()
        self.sp_rest_days.setRange(1, 14)
        self.sp_rest_days.setValue(1)
        self.sp_rest_days.valueChanged.connect(self.update_preview)
        cyc_layout.addRow("Días de descanso continuo:", self.sp_rest_days)
        self.panel_cycle.setVisible(False)
        rr_layout.addWidget(self.panel_cycle)

        self.widget_rotating_rest.setVisible(False)
        rest_vbox.addWidget(self.widget_rotating_rest)

        self.rb_rest_fixed.toggled.connect(self._on_rest_mode_changed)
        left_layout.addWidget(gb_rest)
        left_layout.addStretch()

        scroll.setWidget(left_widget)
        splitter.addWidget(scroll)

        # ====================================================================
        # PANEL DERECHO: PREVISUALIZACIÓN EN VIVO (30 DÍAS)
        # ====================================================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        prev_head = QHBoxLayout()
        prev_title = QLabel("📅 Previsualización del Rol (Próximos 30 Días)")
        prev_title.setObjectName("h3Title")
        prev_head.addWidget(prev_title)
        prev_head.addStretch()

        self.lbl_preview_stats = QLabel("Calculando...")
        self.lbl_preview_stats.setObjectName("mutedLabel")
        prev_head.addWidget(self.lbl_preview_stats)
        right_layout.addLayout(prev_head)

        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(4)
        self.table_preview.setHorizontalHeaderLabels(["Fecha", "Día", "Turno Programado", "Estado"])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.table_preview)

        splitter.addWidget(right_widget)
        splitter.setSizes([500, 520])
        main_layout.addWidget(splitter)

        # Botones inferiores
        btn_bar = QHBoxLayout()
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #FF5252; font-weight: bold;")
        btn_bar.addWidget(self.lbl_error)
        btn_bar.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Guardar Horario")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._save_schedule)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

    # ------------------------------------------------------------------------
    # MÉTODOS DE MANEJO DE ESTADO UI
    # ------------------------------------------------------------------------

    def _on_shift_mode_changed(self) -> None:
        is_fixed = self.rb_shift_fixed.isChecked()
        self.widget_fixed_shift.setVisible(is_fixed)
        self.widget_rotating_shift.setVisible(not is_fixed)
        self.update_preview()

    def _on_rest_mode_changed(self) -> None:
        is_fixed = self.rb_rest_fixed.isChecked()
        self.widget_fixed_rest.setVisible(is_fixed)
        self.widget_rotating_rest.setVisible(not is_fixed)
        self.update_preview()

    def _on_rot_type_changed(self) -> None:
        mode = self.cb_rot_type.currentData()
        self.panel_rolling.setVisible(mode == "rolling")
        self.panel_alt.setVisible(mode == "alternating")
        self.panel_cycle.setVisible(mode == "cycle")
        self.update_preview()

    def _set_rest_presets(self, day_indices: list[int]) -> None:
        for idx, chk in enumerate(self.chk_days):
            chk.setChecked(idx in day_indices)
        self.update_preview()

    def _add_shift_to_list(self, shift_id: int) -> None:
        s = self.shifts_map.get(shift_id)
        if s:
            txt = f"Turno #{s.id}: {s.name} ({s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')})"
            self.list_rot_shifts.addItem(txt)

    def _add_rotating_shift_item(self) -> None:
        sid = self.cb_add_shift.currentData()
        if sid is not None:
            self._add_shift_to_list(sid)
            self.update_preview()

    def _rem_rotating_shift_item(self) -> None:
        row = self.list_rot_shifts.currentRow()
        if row >= 0:
            self.list_rot_shifts.takeItem(row)
            self.update_preview()

    def _get_rotating_shift_ids(self) -> list[int]:
        ids: list[int] = []
        for i in range(self.list_rot_shifts.count()):
            item_text = self.list_rot_shifts.item(i).text()
            # Formato: "Turno #ID: ..."
            if "Turno #" in item_text:
                try:
                    sid_str = item_text.split("Turno #")[1].split(":")[0]
                    ids.append(int(sid_str))
                except (IndexError, ValueError):
                    pass
        return ids

    # ------------------------------------------------------------------------
    # PREVISUALIZACIÓN EN TIEMPO REAL
    # ------------------------------------------------------------------------

    def _build_config_from_ui(self) -> SchedulePlanConfig:
        pin = self.cb_employee.currentData() or ""
        q_from = self.dt_from.date()
        valid_from = date(q_from.year(), q_from.month(), q_from.day())

        valid_until = None
        if not self.chk_indefinite.isChecked():
            q_to = self.dt_until.date()
            valid_until = date(q_to.year(), q_to.month(), q_to.day())

        # Turno
        if self.rb_shift_fixed.isChecked():
            shift_mode = ShiftModeOption.FIXED
            fixed_id = self.cb_fixed_shift.currentData()
            rot_ids = None
            freq_weeks = 1
        else:
            shift_mode = ShiftModeOption.ROTATING
            fixed_id = None
            rot_ids = self._get_rotating_shift_ids()
            freq_weeks = self.cb_shift_freq.currentData() or 1

        # Descanso
        if self.rb_rest_fixed.isChecked():
            rest_mode = RestModeOption.FIXED
            fixed_rest = {idx for idx, chk in enumerate(self.chk_days) if chk.isChecked()}
            roll_start = 6
            roll_freq = 1
            alt_days = None
            alt_freq = 1
            cyc_work = 6
            cyc_rest = 1
        else:
            rot_type = self.cb_rot_type.currentData()
            if rot_type == "rolling":
                rest_mode = RestModeOption.ROLLING
                fixed_rest = None
                roll_start = self.cb_roll_start.currentData() or 6
                roll_freq = self.cb_roll_freq.currentData() or 1
                alt_days = None
                alt_freq = 1
                cyc_work = 6
                cyc_rest = 1
            elif rot_type == "alternating":
                rest_mode = RestModeOption.ALTERNATING
                fixed_rest = None
                roll_start = 6
                roll_freq = 1
                alt_days = [self.cb_alt_day1.currentData() or 6, self.cb_alt_day2.currentData() or 5]
                alt_freq = self.cb_alt_freq.currentData() or 1
                cyc_work = 6
                cyc_rest = 1
            else:
                rest_mode = RestModeOption.WORK_REST_CYCLE
                fixed_rest = None
                roll_start = 6
                roll_freq = 1
                alt_days = None
                alt_freq = 1
                cyc_work = self.sp_work_days.value()
                cyc_rest = self.sp_rest_days.value()

        return SchedulePlanConfig(
            employee_pin=pin,
            valid_from=valid_from,
            valid_until=valid_until,
            shift_mode=shift_mode,
            fixed_shift_id=fixed_id,
            rotating_shift_ids=rot_ids,
            shift_frequency_weeks=freq_weeks,
            rest_mode=rest_mode,
            fixed_rest_weekdays=fixed_rest,
            rolling_initial_weekday=roll_start,
            rolling_interval_weeks=roll_freq,
            alternating_rest_weekdays=alt_days,
            alternating_interval_weeks=alt_freq,
            cycle_work_days=cyc_work,
            cycle_rest_days=cyc_rest,
        )

    def update_preview(self) -> None:
        """Actualiza la tabla de 30 días calculando dinámicamente el rol."""
        try:
            config = self._build_config_from_ui()
            preview = SchedulePlanBuilder.generate_preview(config, self.shifts_map, days=30)
            self.lbl_error.setText("")
        except ValidationError as e:
            self.lbl_error.setText(f"⚠ {e}")
            self.lbl_preview_stats.setText("Configuración incompleta")
            return

        self.table_preview.setRowCount(len(preview))
        work_days_count = 0
        rest_days_count = 0

        for row, p in enumerate(preview):
            item_date = QTableWidgetItem(p.date.strftime("%Y-%m-%d"))
            item_day = QTableWidgetItem(p.day_name)
            item_shift = QTableWidgetItem(f"{p.shift_name} ({p.time_range_str})")

            if p.is_rest_day:
                rest_days_count += 1
                item_status = QTableWidgetItem("DESCANSO")
                item_status.setForeground(QColor("#FFA726"))  # Naranja
                item_date.setForeground(QColor("#FFA726"))
                item_day.setForeground(QColor("#FFA726"))
                item_shift.setForeground(QColor("#8E8E93"))
            else:
                work_days_count += 1
                item_status = QTableWidgetItem("LABORABLE")
                item_status.setForeground(QColor("#4CAF50"))  # Verde

            self.table_preview.setItem(row, 0, item_date)
            self.table_preview.setItem(row, 1, item_day)
            self.table_preview.setItem(row, 2, item_shift)
            self.table_preview.setItem(row, 3, item_status)

        self.lbl_preview_stats.setText(
            f"Próximos 30 días: {work_days_count} días de trabajo | {rest_days_count} descansos"
        )

    # ------------------------------------------------------------------------
    # GUARDAR
    # ------------------------------------------------------------------------

    def _save_schedule(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            QMessageBox.critical(self, "Error", "No hay conexión activa a la base de datos.")
            return

        try:
            config = self._build_config_from_ui()
            emp_name = self.cb_employee.currentText().split(" (")[0]
            prefix = f"Rol {emp_name}"
            assignment, pattern = SchedulePlanBuilder.build_assignment_and_pattern(
                config, self.shifts_map, pattern_name_prefix=prefix
            )

            if pattern is not None:
                saved_pattern = bundle.rotation_pattern_repo.save(pattern)
                assignment.rotation_pattern_id = saved_pattern.id

            bundle.schedule_assignment_repo.save(assignment)
            self.state.data_updated.emit("schedules")
            QMessageBox.information(
                self,
                "Horario Asignado",
                f"✔ Horario y días de descanso asignados exitosamente para {emp_name}.",
            )
            self.accept()

        except ValidationError as e:
            QMessageBox.warning(self, "Validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"Ocurrió un error inesperado:\n{e}")

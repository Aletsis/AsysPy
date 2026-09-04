"""Vista de Evaluación Diaria de Jornadas e Incidencias."""

from datetime import date

from PySide6.QtCore import QDate, Qt, QThread, Signal
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
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.application.attendance.process_daily_attendance import ProcessDailyAttendance
from attendance.application.incidence.register_justification import register_justification
from attendance.domain.incidence.enums import JustificationType


class EvaluationWorker(QThread):
    """Evalúa jornadas de empleados en segundo plano."""

    progress = Signal(int, int, str)       # (actual, total, pin)
    finished_eval = Signal(int, int, str)  # (procesados, incidencias, resumen)
    error_occurred = Signal(str)

    def __init__(
        self,
        bundle,
        target_date: date,
        employee_pins: list[str],
    ) -> None:
        super().__init__()
        self.bundle = bundle
        self.target_date = target_date
        self.employee_pins = employee_pins

    def run(self) -> None:
        try:
            processor = ProcessDailyAttendance(
                attendance_repo=self.bundle.attendance_repo,
                daily_attendance_repo=self.bundle.daily_attendance_repo,
                schedule_assignment_repo=self.bundle.schedule_assignment_repo,
                shift_repo=self.bundle.shift_repo,
                rotation_pattern_repo=self.bundle.rotation_pattern_repo,
                incidence_repo=self.bundle.incidence_repo,
                schedule_exception_repo=self.bundle.schedule_exception_repo,
            )

            total = len(self.employee_pins)
            processed = 0
            incidences = 0

            for i, pin in enumerate(self.employee_pins, start=1):
                self.progress.emit(i, total, pin)
                try:
                    res = processor.execute(employee_pin=pin, target_date=self.target_date)
                    processed += 1
                    status_str = res.status.value if hasattr(res.status, "value") else str(res.status)
                    if status_str != "normal":
                        incidences += 1
                except Exception:
                    pass

            msg = f"Evaluación finalizada para {self.target_date}: {processed}/{total} empleados procesados."
            self.finished_eval.emit(processed, incidences, msg)
        except Exception as e:
            self.error_occurred.emit(str(e))


class JustificationDialog(QDialog):
    """Modal para registrar una justificación administrativa."""

    def __init__(
        self,
        app_state: AppState,
        employee_pin: str,
        target_date: date,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.pin = employee_pin
        self.target_date = target_date
        self.setWindowTitle("Registrar Justificación")
        self.setMinimumWidth(450)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        lbl_emp = QLabel(f"Empleado PIN: {self.pin} • Fecha: {self.target_date}")
        lbl_emp.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: bold;")
        layout.addWidget(lbl_emp)

        self.combo_type = QComboBox()
        self.combo_type.addItem("Permiso con Goce de Sueldo", JustificationType.PAID_LEAVE)
        self.combo_type.addItem("Permiso sin Goce de Sueldo", JustificationType.UNPAID_LEAVE)
        self.combo_type.addItem("Incapacidad Médica / IMSS", JustificationType.IMSS_INCAPACITY)
        self.combo_type.addItem("Vacaciones", JustificationType.VACATION)
        self.combo_type.addItem("Comisión de Trabajo", JustificationType.COMMISSION)
        self.combo_type.addItem("Otros", JustificationType.OTHER)

        self.txt_reason = QLineEdit("Cita Médica / Trámite Oficial")
        self.txt_approved_by = QLineEdit("Administrador RRHH")
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Folio de comprobante o notas adicionales...")
        self.txt_notes.setMaximumHeight(80)

        form.addRow("Tipo de Justificación:", self.combo_type)
        form.addRow("Motivo / Causa:", self.txt_reason)
        form.addRow("Aprobado por:", self.txt_approved_by)
        form.addRow("Comprobante / Folio:", self.txt_notes)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Aprobar Justificación")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        reason = self.txt_reason.text().strip()
        approver = self.txt_approved_by.text().strip()
        doc = self.txt_notes.toPlainText().strip() or None
        j_type = self.combo_type.currentData()

        if not reason or not approver:
            QMessageBox.warning(self, "Campos requeridos", "Motivo y aprobador son obligatorios.")
            return

        try:
            register_justification(
                employee_pin=self.pin,
                justification_type=j_type,
                start_date=self.target_date,
                end_date=self.target_date,
                reason=reason,
                approved_by=approver,
                support_document=doc,
                incidence_repo=bundle.incidence_repo,
                employee_repo=bundle.employee_repo,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al justificar", str(e))


class EvaluationView(QWidget):
    """Pantalla para procesar jornadas y gestionar incidencias."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._worker: EvaluationWorker | None = None
        self._setup_ui()
        self.load_results()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Cierre y Evaluación de Asistencias")
        title.setObjectName("h1Title")
        sub = QLabel("Procesamiento de reglas laborales, retardos, horas extra y justificaciones.")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_run_eval = QPushButton("⚡ Ejecutar Evaluación")
        self.btn_run_eval.setObjectName("primaryBtn")
        self.btn_run_eval.clicked.connect(self._run_evaluation)
        top.addWidget(self.btn_run_eval)

        layout.addLayout(top)

        # Barra de Parámetros de Evaluación
        param_bar = QHBoxLayout()
        param_bar.addWidget(QLabel("Fecha a Evaluar:"))
        self.date_eval = QDateEdit()
        self.date_eval.setCalendarPopup(True)
        d_today = date.today()
        self.date_eval.setDate(QDate(d_today.year, d_today.month, d_today.day))
        self.date_eval.dateChanged.connect(self.load_results)
        param_bar.addWidget(self.date_eval)

        param_bar.addWidget(QLabel("Colaborador:"))
        self.combo_emp_filter = QComboBox()
        self.combo_emp_filter.addItem("Todos los colaboradores", None)
        self._fill_employees_combo()
        param_bar.addWidget(self.combo_emp_filter)

        self.btn_refresh = QPushButton("🔄 Recargar")
        self.btn_refresh.clicked.connect(self.load_results)
        param_bar.addWidget(self.btn_refresh)

        self.btn_justify = QPushButton("📝 Justificar Incidencia Seleccionada")
        self.btn_justify.clicked.connect(self._justify_selected)
        param_bar.addWidget(self.btn_justify)

        param_bar.addStretch()
        layout.addLayout(param_bar)

        # Barra de progreso
        self.prog_container = QWidget()
        self.prog_container.setVisible(False)
        p_layout = QVBoxLayout(self.prog_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_prog = QLabel("Evaluando...")
        self.lbl_prog.setObjectName("mutedLabel")
        self.prog_bar = QProgressBar()
        p_layout.addWidget(self.lbl_prog)
        p_layout.addWidget(self.prog_bar)
        layout.addWidget(self.prog_container)

        # Tabla de Jornadas Evaluadas
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "PIN", "Colaborador", "Entrada", "Salida", "Min. Laborados", "Retardo (min)", "Extra (min)", "Estado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _fill_employees_combo(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return
        try:
            employees = bundle.employee_repo.list_all()
            for emp in employees:
                self.combo_emp_filter.addItem(f"{emp.pin} - {emp.full_name}", emp.pin)
        except Exception:
            pass

    def load_results(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        py_eval = self.date_eval.date()
        target_d = date(py_eval.year(), py_eval.month(), py_eval.day())
        emp_filter = self.combo_emp_filter.currentData()

        try:
            daily_records = bundle.daily_attendance_repo.list_by_date(target_d)
            employees_map = {e.pin: e.full_name for e in bundle.employee_repo.list_all()}

            if emp_filter:
                daily_records = [d for d in daily_records if d.employee_pin == emp_filter]

            self.table.setRowCount(len(daily_records))
            for row, d in enumerate(daily_records):
                self.table.setItem(row, 0, QTableWidgetItem(str(d.employee_pin)))
                emp_name = employees_map.get(d.employee_pin, "Desconocido")
                self.table.setItem(row, 1, QTableWidgetItem(emp_name))

                in_str = d.first_check_in.strftime("%H:%M:%S") if d.first_check_in else "--:--:--"
                out_str = d.last_check_out.strftime("%H:%M:%S") if d.last_check_out else "--:--:--"
                self.table.setItem(row, 2, QTableWidgetItem(in_str))
                self.table.setItem(row, 3, QTableWidgetItem(out_str))

                self.table.setItem(row, 4, QTableWidgetItem(str(d.total_worked_minutes)))
                self.table.setItem(row, 5, QTableWidgetItem(str(d.tardiness_minutes)))
                self.table.setItem(row, 6, QTableWidgetItem(str(d.overtime_minutes)))

                status_val = d.status.value if hasattr(d.status, "value") else str(d.status)
                status_item = QTableWidgetItem(status_val.upper())
                if status_val == "present":
                    status_item.setForeground(Qt.GlobalColor.green)
                elif "tardy" in status_val or "early" in status_val:
                    status_item.setForeground(Qt.GlobalColor.yellow)
                elif status_val == "absent":
                    status_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(row, 7, status_item)
        except Exception:
            pass

    def _run_evaluation(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        py_eval = self.date_eval.date()
        target_d = date(py_eval.year(), py_eval.month(), py_eval.day())
        emp_filter = self.combo_emp_filter.currentData()

        if emp_filter:
            pins = [emp_filter]
        else:
            employees = bundle.employee_repo.list_all()
            pins = [e.pin for e in employees if e.active]

        if not pins:
            QMessageBox.information(self, "Sin colaboradores", "No hay colaboradores activos para evaluar.")
            return

        self.btn_run_eval.setEnabled(False)
        self.prog_container.setVisible(True)
        self.prog_bar.setRange(0, len(pins))
        self.prog_bar.setValue(0)

        self._worker = EvaluationWorker(bundle=bundle, target_date=target_d, employee_pins=pins)
        self._worker.progress.connect(self._on_eval_progress)
        self._worker.finished_eval.connect(self._on_eval_finished)
        self._worker.error_occurred.connect(self._on_eval_error)
        self._worker.start()

    def _on_eval_progress(self, current: int, total: int, pin: str) -> None:
        self.prog_bar.setValue(current)
        self.lbl_prog.setText(f"Evaluando colaborador {pin} ({current}/{total})...")

    def _on_eval_finished(self, processed: int, incidences: int, msg: str) -> None:
        self.btn_run_eval.setEnabled(True)
        self.prog_container.setVisible(False)
        self.load_results()
        self.state.notify(f"{msg} ({incidences} incidencias detectadas).", "success")

    def _on_eval_error(self, err: str) -> None:
        self.btn_run_eval.setEnabled(True)
        self.prog_container.setVisible(False)
        self.state.notify(f"Error durante evaluación: {err}", "error")

    def _justify_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Seleccione una fila para justificar.")
            return
        item = self.table.item(row, 0)
        if not item or not item.text():
            return
        pin = item.text()
        py_eval = self.date_eval.date()
        target_d = date(py_eval.year(), py_eval.month(), py_eval.day())

        dialog = JustificationDialog(self.state, employee_pin=pin, target_date=target_d, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.state.notify(f"Justificación registrada para el empleado {pin}.", "success")
            self.load_results()

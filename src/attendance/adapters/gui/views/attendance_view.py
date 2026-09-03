"""Vista de Marcaciones y Registro de Asistencias (Attendance Logs)."""

import csv
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
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


class AttendanceView(QWidget):
    """Pantalla para consultar registros crudos de biometricos y sesiones emparejadas."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._setup_ui()
        self.load_data()

        self.state.data_updated.connect(lambda k: self.load_data() if k in ("all", "attendance") else None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Marcaciones y Asistencia")
        title.setObjectName("h1Title")
        sub = QLabel("Consulta de eventos biométricos capturados y jornadas calculadas.")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_export = QPushButton("📥 Exportar a CSV")
        self.btn_export.clicked.connect(self._export_csv)
        top.addWidget(self.btn_export)

        layout.addLayout(top)

        # Filtros de búsqueda y rango de fechas
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Desde:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        d_from = date.today() - timedelta(days=7)
        self.date_from.setDate(QDate(d_from.year, d_from.month, d_from.day))
        filter_bar.addWidget(self.date_from)

        filter_bar.addWidget(QLabel("Hasta:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        d_to = date.today()
        self.date_to.setDate(QDate(d_to.year, d_to.month, d_to.day))
        filter_bar.addWidget(self.date_to)

        self.txt_pin_filter = QLineEdit()
        self.txt_pin_filter.setPlaceholderText("Filtrar por PIN...")
        self.txt_pin_filter.setMaximumWidth(150)
        filter_bar.addWidget(self.txt_pin_filter)

        self.btn_search = QPushButton("🔍 Filtrar")
        self.btn_search.setObjectName("primaryBtn")
        self.btn_search.clicked.connect(self.load_data)
        filter_bar.addWidget(self.btn_search)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # Pestañas: Marcaciones Crudas (RAW) vs Jornadas Diarias
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Pestaña 1: Marcaciones Crudas
        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(7)
        self.raw_table.setHorizontalHeaderLabels([
            "ID", "UID Reloj", "Fecha y Hora", "PIN Empleado", "Reloj ID", "Método", "Estado"
        ])
        self.raw_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.raw_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.raw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        raw_layout.addWidget(self.raw_table)
        self.tabs.addTab(self.raw_tab, "Marcaciones Crudas (Hardware)")

        # Pestaña 2: Jornadas Diarias Emparejadas
        self.daily_tab = QWidget()
        daily_layout = QVBoxLayout(self.daily_tab)
        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(8)
        self.daily_table.setHorizontalHeaderLabels([
            "Fecha", "PIN", "Entrada", "Salida", "Min. Laborados", "Retardo", "Extra", "Estado"
        ])
        self.daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.daily_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.daily_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        daily_layout.addWidget(self.daily_table)
        self.tabs.addTab(self.daily_tab, "Jornadas Diarias Evaluadas")

    def load_data(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        py_start = self.date_from.date()
        start_d = date(py_start.year(), py_start.month(), py_start.day())
        py_end = self.date_to.date()
        end_d = date(py_end.year(), py_end.month(), py_end.day())
        pin_filter = self.txt_pin_filter.text().strip()

        # 1. Cargar marcaciones crudas
        try:
            all_logs = bundle.attendance_repo.list_all()
            raw_logs = [log for log in all_logs if log.timestamp and start_d <= log.timestamp.date() <= end_d]
            if pin_filter:
                raw_logs = [log for log in raw_logs if pin_filter in str(log.employee_pin)]

            self.raw_table.setRowCount(len(raw_logs))
            for row, log in enumerate(raw_logs):
                self.raw_table.setItem(row, 0, QTableWidgetItem(str(log.id or "-")))
                self.raw_table.setItem(row, 1, QTableWidgetItem(str(log.record_uid)))
                ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "-"
                self.raw_table.setItem(row, 2, QTableWidgetItem(ts_str))
                self.raw_table.setItem(row, 3, QTableWidgetItem(str(log.employee_pin)))
                self.raw_table.setItem(row, 4, QTableWidgetItem(str(log.device_id)))
                auth_str = log.auth_method.value if hasattr(log.auth_method, "value") else str(log.auth_method)
                self.raw_table.setItem(row, 5, QTableWidgetItem(auth_str))
                status_str = log.processing_status.value if hasattr(log.processing_status, "value") else str(log.processing_status)
                self.raw_table.setItem(row, 6, QTableWidgetItem(status_str))
        except Exception:
            pass

        # 2. Cargar jornadas diarias evaluadas
        try:
            all_daily = bundle.daily_attendance_repo.list_all()
            daily_records = [d for d in all_daily if start_d <= d.date <= end_d]
            if pin_filter:
                daily_records = [d for d in daily_records if pin_filter in str(d.employee_pin)]

            self.daily_table.setRowCount(len(daily_records))
            for row, d in enumerate(daily_records):
                self.daily_table.setItem(row, 0, QTableWidgetItem(str(d.date)))
                self.daily_table.setItem(row, 1, QTableWidgetItem(str(d.employee_pin)))
                in_str = d.first_check_in.strftime("%H:%M:%S") if d.first_check_in else "--:--:--"
                out_str = d.last_check_out.strftime("%H:%M:%S") if d.last_check_out else "--:--:--"
                self.daily_table.setItem(row, 2, QTableWidgetItem(in_str))
                self.daily_table.setItem(row, 3, QTableWidgetItem(out_str))
                self.daily_table.setItem(row, 4, QTableWidgetItem(str(d.total_worked_minutes)))
                self.daily_table.setItem(row, 5, QTableWidgetItem(str(d.tardiness_minutes)))
                self.daily_table.setItem(row, 6, QTableWidgetItem(str(d.overtime_minutes)))

                status_val = d.status.value if hasattr(d.status, "value") else str(d.status)
                status_item = QTableWidgetItem(status_val)
                if status_val == "present":
                    status_item.setForeground(Qt.GlobalColor.green)
                elif "tardy" in status_val or "early" in status_val:
                    status_item.setForeground(Qt.GlobalColor.yellow)
                elif status_val == "absent":
                    status_item.setForeground(Qt.GlobalColor.red)
                self.daily_table.setItem(row, 7, status_item)
        except Exception:
            pass

    def _export_csv(self) -> None:
        curr_idx = self.tabs.currentIndex()
        table = self.raw_table if curr_idx == 0 else self.daily_table
        name = "marcaciones_crudas" if curr_idx == 0 else "jornadas_diarias"

        path, _ = QFileDialog.getSaveFileName(self, "Exportar a CSV", f"{name}.csv", "Archivos CSV (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = []
                for c in range(table.columnCount()):
                    h_item = table.horizontalHeaderItem(c)
                    headers.append(h_item.text() if h_item is not None else f"Columna {c}")
                writer.writerow(headers)

                for r in range(table.rowCount()):
                    row_data = []
                    for c in range(table.columnCount()):
                        item = table.item(r, c)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            self.state.notify(f"Archivo exportado con éxito a '{path}'.", "success")
        except Exception as e:
            QMessageBox.critical(self, "Error de exportación", f"No se pudo guardar el archivo: {e}")

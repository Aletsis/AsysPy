"""Vista de Gestión de Relojes Biométricos (Devices) para AsistPy GUI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    QVBoxLayout,
    QWidget,
)

from attendance.adapters.gui.state import AppState
from attendance.adapters.gui.styles.theme import Theme
from attendance.adapters.gui.workers.device_worker import DeviceProbeWorker, DeviceSyncWorker
from attendance.domain.device.device import Device


class DeviceEditDialog(QDialog):
    """Modal para alta y edición de un reloj biométrico."""

    def __init__(
        self,
        app_state: AppState,
        device: Device | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = app_state
        self.device = device
        self.setWindowTitle("Editar Reloj Biométrico" if device else "Registrar Nuevo Reloj")
        self.setMinimumWidth(500)
        self.setStyleSheet(Theme.get_stylesheet())

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        self.txt_name = QLineEdit(self.device.name if self.device else "Reloj Entrada Principal")
        self.txt_ip = QLineEdit(self.device.ip_address if self.device else "192.168.1.201")
        self.txt_port = QLineEdit(str(self.device.port or 4370) if self.device else "4370")
        self.txt_serial = QLineEdit(self.device.serial_number if self.device else "")
        self.txt_serial.setPlaceholderText("Opcional (se autodetecta al probar)")
        self.txt_location = QLineEdit(self.device.location_label or "" if self.device else "")
        self.txt_location.setPlaceholderText("Ej. Torniquetes Acceso A")

        self.combo_branch = QComboBox()
        self.combo_branch.addItem("Sin sucursal asignada (General)", 0)
        branches = self.state.bundle.branch_repo.list_all() if self.state.bundle else []
        selected_idx = 0
        for i, b in enumerate(branches, start=1):
            if b.id is not None:
                self.combo_branch.addItem(b.name, b.id)
                if self.device and self.device.branch_id == b.id:
                    selected_idx = i
        self.combo_branch.setCurrentIndex(selected_idx)

        form.addRow("Nombre descriptivo (*):", self.txt_name)
        form.addRow("Dirección IP (*):", self.txt_ip)
        form.addRow("Puerto TCP (ZK):", self.txt_port)
        form.addRow("Número de Serie:", self.txt_serial)
        form.addRow("Ubicación Física:", self.txt_location)
        form.addRow("Sucursal asignada:", self.combo_branch)
        layout.addLayout(form)

        # Probar conexión previa
        test_row = QHBoxLayout()
        self.btn_probe = QPushButton("📡 Probar Comunicación TCP")
        self.btn_probe.clicked.connect(self._on_probe)
        test_row.addWidget(self.btn_probe)
        layout.addLayout(test_row)

        self.lbl_probe_res = QLabel("")
        self.lbl_probe_res.setWordWrap(True)
        layout.addWidget(self.lbl_probe_res)

        # Botones de acción
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Guardar Dispositivo")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._on_save)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _on_probe(self) -> None:
        ip = self.txt_ip.text().strip()
        port = int(self.txt_port.text().strip() or "4370")
        self.btn_probe.setEnabled(False)
        self.lbl_probe_res.setText("Probando conexión...")
        self.lbl_probe_res.setStyleSheet("color: #276EF1;")

        self._worker = DeviceProbeWorker(ip=ip, port=port)
        self._worker.finished_probe.connect(self._probe_done)
        self._worker.start()

    def _probe_done(self, success: bool, msg: str, info: dict) -> None:
        self.btn_probe.setEnabled(True)
        if success:
            fw = info.get("firmware_version", info.get("firmware", ""))
            serial = info.get("serial_number", "")
            if serial and not self.txt_serial.text().strip():
                self.txt_serial.setText(serial)
            details = []
            if fw:
                details.append(f"FW: {fw}")
            if serial:
                details.append(f"Serie: {serial}")
            extra = f" [{', '.join(details)}]" if details else ""
            self.lbl_probe_res.setText(f"✓ {msg}{extra}")
            self.lbl_probe_res.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.lbl_probe_res.setText(f"✗ {msg}")
            self.lbl_probe_res.setStyleSheet("color: #EF4444;")

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        ip = self.txt_ip.text().strip()
        if not name or not ip:
            QMessageBox.warning(self, "Campos requeridos", "Debe ingresar nombre y dirección IP.")
            return

        port = int(self.txt_port.text().strip() or "4370")
        branch_id = self.combo_branch.currentData() or 0
        serial = self.txt_serial.text().strip()
        location = self.txt_location.text().strip() or None

        bundle = self.state.bundle
        if not bundle:
            return

        if self.device:
            self.device.name = name
            self.device.ip_address = ip
            self.device.port = port
            self.device.branch_id = branch_id
            self.device.serial_number = serial
            self.device.location_label = location
            bundle.device_repo.save(self.device)
        else:
            new_dev = Device(
                id=None,
                name=name,
                ip_address=ip,
                port=port,
                serial_number=serial,
                location_label=location,
                branch_id=branch_id,
                active=True,
            )
            bundle.device_repo.save(new_dev)

        self.accept()


class DevicesView(QWidget):
    """Pantalla para administrar y sincronizar el catálogo de relojes."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = app_state
        self._active_probe = None
        self._active_sync = None
        self._setup_ui()
        self.refresh_devices()

        self.state.data_updated.connect(lambda k: self.refresh_devices() if k in ("all", "devices") else None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Encabezado
        top = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Relojes Biométricos")
        title.setObjectName("h1Title")
        sub = QLabel("Catálogo de terminales biométricas ZKTeco por TCP/IP.")
        sub.setObjectName("mutedLabel")
        header.addWidget(title)
        header.addWidget(sub)
        top.addLayout(header)
        top.addStretch()

        self.btn_new = QPushButton("+ Registrar Reloj")
        self.btn_new.setObjectName("primaryBtn")
        self.btn_new.clicked.connect(self._add_device)
        top.addWidget(self.btn_new)

        layout.addLayout(top)

        # Barra de acciones sobre selección
        actions_bar = QHBoxLayout()
        self.btn_sync_sel = QPushButton("⚡ Sincronizar Seleccionado")
        self.btn_sync_sel.clicked.connect(self._sync_selected)
        self.btn_probe_sel = QPushButton("📡 Probar Conexión")
        self.btn_probe_sel.clicked.connect(self._probe_selected)
        self.btn_edit = QPushButton("✏️ Editar")
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_toggle_active = QPushButton("Activar / Desactivar")
        self.btn_toggle_active.clicked.connect(self._toggle_active)
        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.clicked.connect(self._delete_device)

        actions_bar.addWidget(self.btn_sync_sel)
        actions_bar.addWidget(self.btn_probe_sel)
        actions_bar.addWidget(self.btn_edit)
        actions_bar.addWidget(self.btn_toggle_active)
        actions_bar.addWidget(self.btn_delete)
        actions_bar.addStretch()
        layout.addLayout(actions_bar)

        # Tabla de dispositivos
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Dirección IP", "Puerto", "Sucursal", "Ubicación", "Estado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh_devices(self) -> None:
        bundle = self.state.bundle
        if not bundle:
            return

        try:
            devices = bundle.device_repo.list_all()
            branches_map = {b.id: b.name for b in bundle.branch_repo.list_all() if b.id is not None}

            self.table.setRowCount(len(devices))
            for row, dev in enumerate(devices):
                self.table.setItem(row, 0, QTableWidgetItem(str(dev.id or "-")))
                self.table.setItem(row, 1, QTableWidgetItem(dev.name))
                self.table.setItem(row, 2, QTableWidgetItem(dev.ip_address or "-"))
                self.table.setItem(row, 3, QTableWidgetItem(str(dev.port or 4370)))

                branch_name = branches_map.get(dev.branch_id, "General") if dev.branch_id else "General"
                self.table.setItem(row, 4, QTableWidgetItem(branch_name))
                self.table.setItem(row, 5, QTableWidgetItem(dev.location_label or "-"))

                status_item = QTableWidgetItem("ACTIVO" if dev.active else "INACTIVO")
                if dev.active:
                    status_item.setForeground(Qt.GlobalColor.green)
                else:
                    status_item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(row, 6, status_item)
        except Exception:
            pass

    def _get_selected_device(self) -> Device | None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Por favor seleccione un reloj de la lista.")
            return None
        dev_id_item = self.table.item(row, 0)
        if not dev_id_item or not dev_id_item.text():
            return None
        dev_id = int(dev_id_item.text())
        bundle = self.state.bundle
        return bundle.device_repo.get_by_id(dev_id) if bundle else None

    def _add_device(self) -> None:
        dialog = DeviceEditDialog(self.state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_devices()
            self.state.data_updated.emit("devices")
            self.state.notify("Reloj registrado exitosamente.", "success")

    def _edit_selected(self) -> None:
        dev = self._get_selected_device()
        if not dev:
            return
        dialog = DeviceEditDialog(self.state, device=dev, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_devices()
            self.state.data_updated.emit("devices")
            self.state.notify("Reloj actualizado correctamente.", "success")

    def _toggle_active(self) -> None:
        dev = self._get_selected_device()
        if not dev or not self.state.bundle:
            return
        dev.active = not dev.active
        self.state.bundle.device_repo.save(dev)
        self.refresh_devices()
        self.state.data_updated.emit("devices")
        msg = f"Reloj '{dev.name}' {'activado' if dev.active else 'desactivado'}."
        self.state.notify(msg, "info")

    def _delete_device(self) -> None:
        dev = self._get_selected_device()
        if not dev or not dev.id or not self.state.bundle:
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el reloj biométrico '{dev.name}' (ID: {dev.id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.state.bundle.device_repo.delete(dev.id)
            if success:
                self.refresh_devices()
                self.state.data_updated.emit("devices")
                self.state.notify(f"Reloj '{dev.name}' eliminado.", "success")
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el reloj.")

    def _probe_selected(self) -> None:
        dev = self._get_selected_device()
        if not dev or not dev.ip_address:
            return
        self.state.notify(f"Probando comunicación con '{dev.name}' ({dev.ip_address})...", "info")
        worker = DeviceProbeWorker(ip=dev.ip_address, port=dev.port or 4370)
        worker.finished_probe.connect(
            lambda success, msg, info: self.state.notify(msg, "success" if success else "error")
        )
        worker.start()
        self._active_probe = worker

    def _sync_selected(self) -> None:
        dev = self._get_selected_device()
        if not dev or not self.state.bundle:
            return
        if not dev.active:
            QMessageBox.warning(self, "Reloj Inactivo", "El reloj seleccionado está inactivo. Actívelo primero.")
            return

        self.state.notify(f"Sincronizando '{dev.name}'...", "info")
        worker = DeviceSyncWorker(bundle=self.state.bundle, device_id=dev.id)
        worker.finished_sync.connect(self._on_device_sync_done)
        worker.error_occurred.connect(lambda err: self.state.notify(err, "error"))
        worker.start()
        self._active_sync = worker

    def _on_device_sync_done(self, success: bool, msg: str, total: int) -> None:
        self.state.notify(msg, "success" if success else "warning")
        self.state.data_updated.emit("attendance")

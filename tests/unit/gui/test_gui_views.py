"""Pruebas unitarias para vistas, modales y tema de la GUI de AsistPy."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from attendance.adapters.gui.config import ConfigManager
from attendance.adapters.gui.main_window import MainWindow
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
    SetupWizardDialog,
)
from attendance.adapters.gui.views.attendance_view import ManualPunchDialog
from attendance.adapters.gui.views.devices_view import DeviceEditDialog
from attendance.adapters.gui.views.employees_view import (
    BranchEditDialog,
    DepartmentEditDialog,
    EmployeeDetailDialog,
    EmployeeEditDialog,
    PositionAssignDeptDialog,
    PositionEditDialog,
)
from attendance.adapters.gui.views.schedule_dialog import SetEmployeeScheduleDialog
from attendance.adapters.gui.views.schedules_view import AssignmentDialog, ShiftEditDialog
from attendance.domain.organization.branch import Branch
from attendance.domain.organization.department import Department
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.organization.position import Position
from attendance.domain.schedule.enums import ShiftCategory
from attendance.domain.schedule.shift import ShiftDefinition


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Fixture de QApplication en modo offscreen para pruebas en entornos headless."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_app_state(tmp_path: Path) -> AppState:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    cm.save(backend="memory", database_url="memory://", first_run_completed=True)
    state = AppState(config_manager=cm)

    # Inicializar catálogo base de prueba en memoria
    if state.bundle:
        b = Branch(id=None, code="SUC1", name="Sucursal Matriz", timezone="America/Mexico_City")
        saved_b = state.bundle.branch_repo.save(b)
        d = Department(id=None, code="TI", name="Tecnología", branch_id=saved_b.id)
        state.bundle.department_repo.save(d)
        if state.bundle.position_repo:
            p = Position(id=None, code="DEV", name="Desarrollador", description="Programación")
            saved_p = state.bundle.position_repo.save(p)
            state.bundle.position_repo.assign_department(saved_p.id, d.id)

    return state


def test_theme_contains_user_palette() -> None:
    stylesheet = Theme.get_stylesheet()
    assert "#09091A" in stylesheet
    assert "#FFFFFF" in stylesheet
    assert "#276EF1" in stylesheet
    assert "#6B6B6B" in stylesheet


def test_setup_wizard_dialog_instantiation(qapp: QApplication, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    cm = ConfigManager(env_path=env_file)
    wizard = SetupWizardDialog(config_manager=cm)
    assert wizard is not None
    assert wizard.windowTitle() == "AsistPy - Asistente de Configuración Inicial"


def test_views_instantiation(qapp: QApplication, mock_app_state: AppState) -> None:
    dash = DashboardView(mock_app_state)
    assert dash is not None

    devs = DevicesView(mock_app_state)
    assert devs is not None

    emps = EmployeesView(mock_app_state)
    assert emps is not None
    assert emps.tabs.count() == 4
    assert emps.tabs.tabText(0) == "Colaboradores"
    assert emps.tabs.tabText(1) == "Puestos / Cargos"
    assert emps.tabs.tabText(2) == "Departamentos"
    assert emps.tabs.tabText(3) == "Sucursales"

    sched = SchedulesView(mock_app_state)
    assert sched is not None
    assert sched.tabs.count() == 4
    assert sched.tabs.tabText(0) == "Catálogo de Turnos"
    assert sched.tabs.tabText(1) == "Asignaciones de Horario"
    assert sched.tabs.tabText(2) == "Patrones de Rotación"
    assert sched.tabs.tabText(3) == "Excepciones y Eventualidades"

    att = AttendanceView(mock_app_state)
    assert att is not None
    assert att.tabs.count() == 2

    eval_v = EvaluationView(mock_app_state)
    assert eval_v is not None

    sett = SettingsView(mock_app_state)
    assert sett is not None


def test_main_window_navigation(qapp: QApplication, mock_app_state: AppState) -> None:
    win = MainWindow(mock_app_state)
    assert win is not None
    assert win.stack.count() == 7
    win._on_nav_clicked(1)
    assert win.stack.currentIndex() == 1


def test_employee_edit_and_detail_dialogs(qapp: QApplication, mock_app_state: AppState) -> None:
    # 1. Crear nuevo colaborador vía modal
    dialog = EmployeeEditDialog(mock_app_state)
    dialog.txt_pin.setText("E888")
    dialog.txt_first_name.setText("Juan")
    dialog.txt_paternal.setText("Perez")
    dialog.txt_maternal.setText("Lopez")
    dialog.txt_curp.setText("PELJ900101HDFRRN01")
    dialog.txt_rfc.setText("PELJ900101AB1")
    dialog.txt_email.setText("juan.perez@empresa.com")
    dialog.txt_phone.setText("5512345678")
    dialog.txt_password.setText("1234")
    dialog.txt_card.setText("RFID_888")

    dialog._on_save()
    emp = mock_app_state.bundle.employee_repo.get_by_pin("E888")
    assert emp is not None
    assert emp.first_name == "Juan"
    assert emp.paternal_last_name == "Perez"
    assert emp.curp == "PELJ900101HDFRRN01"
    assert emp.rfc == "PELJ900101AB1"
    assert emp.email == "juan.perez@empresa.com"
    assert emp.phone_number == "5512345678"
    assert emp.password == "1234"
    assert emp.card_number == "RFID_888"

    # 2. Ver ficha de detalle
    detail_dlg = EmployeeDetailDialog(mock_app_state, employee=emp)
    assert detail_dlg is not None
    assert "E888" in detail_dlg.windowTitle()


def test_position_and_assignment_dialogs(qapp: QApplication, mock_app_state: AppState) -> None:
    # 1. Crear puesto vía modal
    pos_dlg = PositionEditDialog(mock_app_state)
    pos_dlg.txt_code.setText("ANL")
    pos_dlg.txt_name.setText("Analista de Datos")
    pos_dlg.txt_desc.setText("Análisis y visualización")
    pos_dlg._on_save()

    bundle = mock_app_state.bundle
    assert bundle.position_repo is not None
    pos = bundle.position_repo.get_by_code("ANL")
    assert pos is not None
    assert pos.name == "Analista de Datos"

    # 2. Asignar departamento
    assign_dlg = PositionAssignDeptDialog(mock_app_state, position=pos)
    assert assign_dlg.list_widget.count() >= 1
    # Marcar el primer depto
    assign_dlg.list_widget.item(0).setCheckState(pytest.importorskip("PySide6.QtCore").Qt.CheckState.Checked)
    assign_dlg._on_save()

    assigned_depts = bundle.position_repo.get_departments(pos.id)
    assert len(assigned_depts) >= 1


def test_department_and_branch_dialogs(qapp: QApplication, mock_app_state: AppState) -> None:
    # 1. Departamento
    dept_dlg = DepartmentEditDialog(mock_app_state)
    dept_dlg.txt_code.setText("RRHH")
    dept_dlg.txt_name.setText("Recursos Humanos")
    dept_dlg._on_save()

    dept = mock_app_state.bundle.department_repo.get_by_code("RRHH")
    assert dept is not None
    assert dept.name == "Recursos Humanos"

    # 2. Sucursal
    branch_dlg = BranchEditDialog(mock_app_state)
    branch_dlg.txt_code.setText("SUR")
    branch_dlg.txt_name.setText("Sucursal Sur")
    branch_dlg.txt_phone.setText("5599887766")
    branch_dlg.txt_street.setText("Av. Insurgentes 100")
    branch_dlg.txt_city.setText("CDMX")
    branch_dlg._on_save()

    branch = mock_app_state.bundle.branch_repo.get_by_code("SUR")
    assert branch is not None
    assert branch.phone_number == "5599887766"
    assert branch.address is not None
    assert branch.address.street == "Av. Insurgentes 100"


def test_shift_and_assignment_dialogs(qapp: QApplication, mock_app_state: AppState) -> None:
    from PySide6.QtCore import QTime

    # 1. Crear turno nocturno
    shift_dlg = ShiftEditDialog(mock_app_state)
    shift_dlg.txt_name.setText("Nocturno 22:00 - 06:00")
    shift_dlg.combo_category.setCurrentIndex(3)  # NOCTURNO
    shift_dlg.time_start.setTime(QTime(22, 0))
    shift_dlg.time_end.setTime(QTime(6, 0))
    shift_dlg.chk_midnight.setChecked(True)
    shift_dlg._on_save()

    shifts = mock_app_state.bundle.shift_repo.list_all()
    night_shift = [s for s in shifts if s.name == "Nocturno 22:00 - 06:00"]
    assert len(night_shift) == 1
    assert night_shift[0].crosses_midnight is True
    assert night_shift[0].category == ShiftCategory.NOCTURNO

    # 2. Asignar turno a empleado
    emp = Employee(
        id=None,
        pin="E101",
        first_name="Carlos",
        paternal_last_name="Gomez",
        sex=Sex.MALE,
    )
    mock_app_state.bundle.employee_repo.save(emp)

    assign_dlg = AssignmentDialog(mock_app_state)
    assign_dlg.combo_emp.setCurrentIndex(0)
    assign_dlg.combo_shift.setCurrentIndex(0)
    assign_dlg._on_save()

    assignments = mock_app_state.bundle.schedule_assignment_repo.list_all()
    assert len(assignments) >= 1


def test_manual_punch_dialog(qapp: QApplication, mock_app_state: AppState) -> None:
    emp = Employee(
        id=None,
        pin="E202",
        first_name="Maria",
        paternal_last_name="Santos",
        sex=Sex.FEMALE,
    )
    mock_app_state.bundle.employee_repo.save(emp)

    punch_dlg = ManualPunchDialog(mock_app_state)
    # Seleccionar empleado E202
    idx = -1
    for i in range(punch_dlg.combo_emp.count()):
        if "E202" in punch_dlg.combo_emp.itemText(i):
            idx = i
            break
    assert idx >= 0
    punch_dlg.combo_emp.setCurrentIndex(idx)
    punch_dlg.txt_performed_by.setText("supervisor_01")
    punch_dlg.txt_reason.setText("Omisión de registro por falla eléctrica")
    punch_dlg._on_save()

    logs = mock_app_state.bundle.attendance_repo.list_all()
    emp_logs = [log for log in logs if log.employee_pin == "E202"]
    assert len(emp_logs) == 1
    assert emp_logs[0].auth_method.value == "manual"

    # Verificar registro de auditoría correspondiente
    audits = mock_app_state.bundle.audit_repo.list_by_employee("E202")
    assert len(audits) >= 1
    assert audits[0].performed_by == "supervisor_01"
    assert "falla eléctrica" in audits[0].reason


def test_device_edit_dialog(qapp: QApplication, mock_app_state: AppState) -> None:
    dev_dlg = DeviceEditDialog(mock_app_state)
    dev_dlg.txt_name.setText("Reloj Planta Baja")
    dev_dlg.txt_ip.setText("192.168.1.150")
    dev_dlg.txt_port.setText("4370")
    dev_dlg.txt_serial.setText("ZK123456789")
    dev_dlg.txt_location.setText("Recepción")
    dev_dlg._on_save()

    devs = mock_app_state.bundle.device_repo.list_all()
    created = [d for d in devs if d.ip_address == "192.168.1.150"]
    assert len(created) == 1
    assert created[0].serial_number == "ZK123456789"
    assert created[0].location_label == "Recepción"


def test_set_employee_schedule_dialog(qapp: QApplication, mock_app_state: AppState) -> None:
    from datetime import time

    # Preparar colaborador y turnos
    emp = Employee(
        id=None,
        pin="E555",
        first_name="Roberto",
        paternal_last_name="Flores",
        sex=Sex.MALE,
    )
    mock_app_state.bundle.employee_repo.save(emp)

    shift1 = ShiftDefinition(
        id=None,
        name="Matutino 07:00-15:00",
        start_time=time(7, 0),
        end_time=time(15, 0),
        tolerance_minutes=10,
    )
    shift2 = ShiftDefinition(
        id=None,
        name="Vespertino 15:00-23:00",
        start_time=time(15, 0),
        end_time=time(23, 0),
        tolerance_minutes=10,
    )
    mock_app_state.bundle.shift_repo.save(shift1)
    mock_app_state.bundle.shift_repo.save(shift2)

    # 1. Verificar botones en las vistas
    emps_view = EmployeesView(mock_app_state)
    assert hasattr(emps_view, "btn_schedule_emp")
    assert emps_view.btn_schedule_emp.text() == "🗓️ Establecer Horario"

    sched_view = SchedulesView(mock_app_state)
    assert hasattr(sched_view, "btn_set_schedule")
    assert sched_view.btn_set_schedule.text() == "🗓️ Establecer Horario"
    assert hasattr(sched_view, "btn_set_sched_tab")

    # 2. Instanciar diálogo con colaborador preseleccionado
    dlg = SetEmployeeScheduleDialog(mock_app_state, preset_employee_pin="E555")
    assert dlg is not None
    assert dlg.cb_employee.currentData() == "E555"

    # Verificar que se generó la previsualización de 30 días
    assert dlg.table_preview.rowCount() == 30

    # 3. Probar cambio a descanso rotativo rolado
    dlg.rb_rest_rotating.setChecked(True)
    dlg.cb_rot_type.setCurrentIndex(0)  # rolling
    assert dlg.panel_rolling.isHidden() is False
    assert dlg.table_preview.rowCount() == 30

    # 4. Guardar horario
    dlg._save_schedule()

    # Verificar que se persistió el patrón y la asignación
    assignments = mock_app_state.bundle.schedule_assignment_repo.list_all()
    emp_assigns = [a for a in assignments if a.employee_pin == "E555"]
    assert len(emp_assigns) == 1
    assert emp_assigns[0].rotation_pattern_id is not None

    patterns = mock_app_state.bundle.rotation_pattern_repo.list_all()
    assert len(patterns) >= 1


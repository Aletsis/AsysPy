"""Módulo de vistas y pantallas para la GUI de AsistPy."""

from attendance.adapters.gui.views.attendance_view import AttendanceView
from attendance.adapters.gui.views.dashboard_view import DashboardView
from attendance.adapters.gui.views.devices_view import DevicesView
from attendance.adapters.gui.views.employees_view import EmployeesView
from attendance.adapters.gui.views.evaluation_view import EvaluationView
from attendance.adapters.gui.views.schedules_view import SchedulesView
from attendance.adapters.gui.views.settings_view import SettingsView
from attendance.adapters.gui.views.wizard_view import SetupWizardDialog

__all__ = [
    "AttendanceView",
    "DashboardView",
    "DevicesView",
    "EmployeesView",
    "EvaluationView",
    "SchedulesView",
    "SettingsView",
    "SetupWizardDialog",
]

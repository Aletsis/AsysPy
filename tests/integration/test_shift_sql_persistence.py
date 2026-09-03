"""Pruebas de persistencia e integración para el catálogo de turnos y rotaciones SQL."""

from datetime import date, datetime, time
import pytest
from sqlalchemy.orm import Session

from attendance.adapters.persistence.factory import PersistenceFactory
from attendance.application.attendance.process_daily_attendance import ProcessDailyAttendance
from attendance.domain.attendance.enums import AttendanceStatus
from attendance.domain.device.enums import AuthMethod, LogStatus
from attendance.domain.device.log import AttendanceLog
from attendance.domain.organization.employee import Employee, Sex
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import (
    AssignmentMode,
    RotationFrequency,
    ShiftCategory,
)
from attendance.domain.schedule.rotation import RotationPattern
from attendance.domain.schedule.shift import ShiftDefinition, ShiftSegment


@pytest.fixture
def sql_bundle():
    """Crea un bundle relacional SQLite en memoria con tablas creadas."""
    return PersistenceFactory.create_bundle(
        "sqlite", connection_string="sqlite:///:memory:", init_tables=True
    )


def test_catalog_shifts_crud(sql_bundle) -> None:
    repo = sql_bundle.shift_repo

    # 1. Turno Matutino
    morning = ShiftDefinition(
        id=None,
        name="Turno Matutino",
        category=ShiftCategory.MATUTINO,
        start_time=time(7, 0),
        end_time=time(15, 0),
        tolerance_minutes=10,
    )
    s_morning = repo.save(morning)
    assert s_morning.id is not None

    # 2. Turno Vespertino
    evening = ShiftDefinition(
        id=None,
        name="Turno Vespertino",
        category=ShiftCategory.VESPERTINO,
        start_time=time(15, 0),
        end_time=time(23, 0),
        tolerance_minutes=10,
    )
    s_evening = repo.save(evening)
    assert s_evening.id is not None

    # 3. Turno Nocturno (cruza medianoche)
    night = ShiftDefinition(
        id=None,
        name="Turno Nocturno",
        category=ShiftCategory.NOCTURNO,
        start_time=time(23, 0),
        end_time=time(7, 0),
        tolerance_minutes=15,
        crosses_midnight=True,
    )
    s_night = repo.save(night)
    assert s_night.id is not None
    assert s_night.crosses_midnight

    # 4. Turno 24 Horas (Operativo 24x48)
    shift_24 = ShiftDefinition(
        id=None,
        name="Guardia 24 Horas",
        category=ShiftCategory.NOCTURNO,
        start_time=time(8, 0),
        end_time=time(7, 59),
        tolerance_minutes=20,
        crosses_midnight=True,
    )
    s_24 = repo.save(shift_24)
    assert s_24.id is not None
    assert s_24.crosses_midnight

    # 5. Turno Partido (Comercio / Restaurante)
    split = ShiftDefinition(
        id=None,
        name="Turno Partido",
        category=ShiftCategory.MIXTO,
        segments=[
            ShiftSegment(start_time=time(9, 0), end_time=time(13, 0), tolerance_minutes=10, name="Turno 1"),
            ShiftSegment(start_time=time(15, 0), end_time=time(19, 0), tolerance_minutes=5, name="Turno 2"),
        ],
    )
    s_split = repo.save(split)
    assert s_split.id is not None
    assert s_split.is_split

    # Consultas y listado
    shifts = repo.list_all()
    assert len(shifts) == 5

    # Actualización
    s_morning.name = "Matutino 7 a 15 Oficial"
    repo.save(s_morning)
    reloaded = repo.get_by_id(s_morning.id)
    assert reloaded is not None
    assert reloaded.name == "Matutino 7 a 15 Oficial"

    # Eliminación
    assert repo.delete(s_split.id) is True
    assert repo.get_by_id(s_split.id) is None
    assert len(repo.list_all()) == 4


def test_catalog_rotation_patterns_crud(sql_bundle) -> None:
    rot_repo = sql_bundle.rotation_pattern_repo
    shift_repo = sql_bundle.shift_repo

    # Crear turnos de referencia
    s1 = shift_repo.save(ShiftDefinition(id=None, name="Turno 1", category=ShiftCategory.MATUTINO, start_time=time(8, 0), end_time=time(16, 0)))
    s2 = shift_repo.save(ShiftDefinition(id=None, name="Turno 2", category=ShiftCategory.VESPERTINO, start_time=time(16, 0), end_time=time(0, 0), crosses_midnight=True))

    # 1. Patrón 24x48 (1 día de guardia 24h, 2 días de descanso)
    pattern_24x48 = RotationPattern(
        id=None,
        name="Rol 24x48 Seguridad",
        shift_sequence=[s1.id, None, None],
        frequency=RotationFrequency.DAILY,
        anchor_date=date(2026, 1, 1),
    )
    saved_24x48 = rot_repo.save(pattern_24x48)
    assert saved_24x48.id is not None
    assert saved_24x48.shift_sequence == [s1.id, None, None]

    # 2. Patrón Rotativo Quincenal / Semanal
    pattern_weekly = RotationPattern(
        id=None,
        name="Rol Semanal Mañana/Tarde",
        shift_sequence=[s1.id, s2.id],
        frequency=RotationFrequency.WEEKLY,
        anchor_date=date(2026, 1, 5),
    )
    saved_weekly = rot_repo.save(pattern_weekly)
    assert saved_weekly.id is not None

    assert len(rot_repo.list_all()) == 2

    # Actualizar y eliminar
    saved_weekly.name = "Rol Semanal Ajustado"
    rot_repo.save(saved_weekly)
    assert rot_repo.get_by_id(saved_weekly.id).name == "Rol Semanal Ajustado"

    assert rot_repo.delete(saved_weekly.id) is True
    assert len(rot_repo.list_all()) == 1


def test_process_daily_attendance_with_24x48_rotation_from_sql_db(sql_bundle) -> None:
    """Valida la resolución y evaluación integral de un empleado con rol 24x48 cargado de SQL."""
    # 1. Crear y persistir el turno de 24 horas en el catálogo
    guardia_24 = sql_bundle.shift_repo.save(
        ShiftDefinition(
            id=None,
            name="Guardia 24 Horas",
            category=ShiftCategory.NOCTURNO,
            start_time=time(8, 0),
            end_time=time(7, 59),
            tolerance_minutes=15,
            crosses_midnight=True,
        )
    )

    # 2. Crear y persistir el patrón 24x48 en el catálogo
    anchor_date = date(2026, 3, 1)  # Domingo: Día 1 de guardia
    rol_24x48 = sql_bundle.rotation_pattern_repo.save(
        RotationPattern(
            id=None,
            name="Rotación Bomberos / Médicos 24x48",
            shift_sequence=[guardia_24.id, None, None],
            frequency=RotationFrequency.DAILY,
            anchor_date=anchor_date,
        )
    )

    # 3. Registrar empleado
    emp = sql_bundle.employee_repo.save(
        Employee(
            id=None,
            pin="MED001",
            first_name="Carlos",
            paternal_last_name="Ramírez",
            maternal_last_name=None,
            hire_date=date(2025, 1, 1),
            sex=Sex.MALE,
            department_id=1,
            position="Médico de Urgencias",
            home_branch_id=1,
            active=True,
        )
    )

    # 4. Asignar rol rotativo 24x48 al empleado
    sql_bundle.schedule_assignment_repo.save(
        EmployeeScheduleAssignment(
            id=None,
            employee_pin="MED001",
            mode=AssignmentMode.ROTATING,
            valid_from=anchor_date,
            rotation_pattern_id=rol_24x48.id,
        )
    )

    # 5. Guardar marcaciones para el día de guardia (2026-03-01)
    # Entrada 07:55, Salida al día siguiente a las 08:05
    sql_bundle.attendance_repo.save_raw_log(
        AttendanceLog(
            id=None,
            record_uid=101,
            employee_pin="MED001",
            device_id=1,
            timestamp=datetime(2026, 3, 1, 7, 55),
            auth_method=AuthMethod.FACE,
            processing_status=LogStatus.RAW,
        )
    )
    sql_bundle.attendance_repo.save_raw_log(
        AttendanceLog(
            id=None,
            record_uid=102,
            employee_pin="MED001",
            device_id=1,
            timestamp=datetime(2026, 3, 2, 8, 5),
            auth_method=AuthMethod.FACE,
            processing_status=LogStatus.RAW,
        )
    )

    # 6. Instanciar ProcessDailyAttendance inyectando únicamente repositorios
    processor = ProcessDailyAttendance(
        attendance_repo=sql_bundle.attendance_repo,
        daily_attendance_repo=sql_bundle.daily_attendance_repo,
        schedule_assignment_repo=sql_bundle.schedule_assignment_repo,
        shift_repo=sql_bundle.shift_repo,
        rotation_pattern_repo=sql_bundle.rotation_pattern_repo,
    )

    # Evaluar Día 1: Turno 24 Horas
    daily_guardia = processor.execute("MED001", anchor_date)
    assert daily_guardia.employee_pin == "MED001"
    assert daily_guardia.date == anchor_date
    assert daily_guardia.status == AttendanceStatus.PRESENT
    assert daily_guardia.tardiness_minutes == 0
    assert daily_guardia.expected_shift is not None
    assert daily_guardia.expected_shift.name == "Guardia 24 Horas"
    assert len(daily_guardia.sessions) == 1

    # Evaluar Día 2 (2026-03-02): Día de descanso en patrón (índice 1 en la secuencia)
    daily_descanso_1 = processor.execute("MED001", date(2026, 3, 2))
    assert daily_descanso_1.date == date(2026, 3, 2)
    assert daily_descanso_1.expected_shift is None

    # Evaluar Día 3 (2026-03-03): Descanso total sin marcaciones según patrón 24x48 (índice 2 en la secuencia)
    daily_descanso_2 = processor.execute("MED001", date(2026, 3, 3))
    assert daily_descanso_2.date == date(2026, 3, 3)
    assert daily_descanso_2.status == AttendanceStatus.REST_DAY
    assert daily_descanso_2.expected_shift is None

    # Evaluar Día 4 (2026-03-04): Vuelve a ser Guardia 24 Horas (índice 0)
    # Sin marcaciones registradas -> AUSENCIA (ABSENT)
    daily_guardia_2 = processor.execute("MED001", date(2026, 3, 4))
    assert daily_guardia_2.date == date(2026, 3, 4)
    assert daily_guardia_2.status == AttendanceStatus.ABSENT
    assert daily_guardia_2.expected_shift is not None
    assert daily_guardia_2.expected_shift.name == "Guardia 24 Horas"

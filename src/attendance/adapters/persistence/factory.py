"""Factoría central de persistencia (Repository Factory).

Instancia los adaptadores adecuados según la configuración del usuario (memoria,
SQLite, PostgreSQL, MySQL, SQL Server, MongoDB) y verifica dependencias opcionales.
"""

import importlib.util
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.memory import (
    InMemoryAttendanceRepository,
    InMemoryAuditLogRepository,
    InMemoryBranchRepository,
    InMemoryDailyAttendanceRepository,
    InMemoryDeviceRepository,
    InMemoryEmployeeRepository,
    InMemoryIncidenceRepository,
    InMemoryRotationPatternRepository,
    InMemoryScheduleAssignmentRepository,
    InMemoryShiftRepository,
    InMemorySyncStateRepository,
)
from attendance.adapters.persistence.sql.database import Database
from attendance.adapters.persistence.sql.repositories import (
    SqlAttendanceRepository,
    SqlAuditLogRepository,
    SqlBranchRepository,
    SqlDailyAttendanceRepository,
    SqlDeviceRepository,
    SqlEmployeeRepository,
    SqlIncidenceRepository,
    SqlRotationPatternRepository,
    SqlScheduleAssignmentRepository,
    SqlShiftRepository,
    SqlSyncStateRepository,
)
from attendance.ports.attendance import (
    AttendanceRepository,
    DailyAttendanceRepository,
)
from attendance.ports.audit import AuditLogRepository
from attendance.ports.device import DeviceRepository, SyncStateRepository
from attendance.ports.incidence import IncidenceRepository
from attendance.ports.organization import BranchRepository, EmployeeRepository
from attendance.ports.schedule import (
    EmployeeScheduleAssignmentRepository,
    RotationPatternRepository,
    ShiftRepository,
)


@dataclass
class PersistenceBundle:
    """Contenedor de todos los repositorios del sistema según la persistencia elegida."""

    attendance_repo: AttendanceRepository
    daily_attendance_repo: DailyAttendanceRepository
    employee_repo: EmployeeRepository
    branch_repo: BranchRepository
    incidence_repo: IncidenceRepository
    schedule_assignment_repo: EmployeeScheduleAssignmentRepository
    audit_repo: AuditLogRepository
    sync_state_repo: SyncStateRepository
    device_repo: DeviceRepository
    shift_repo: ShiftRepository
    rotation_pattern_repo: RotationPatternRepository
    database: Database | None = None




def check_driver_installed(module_name: str, package_extra: str, db_name: str) -> None:
    """Verifica si un driver opcional está instalado y provee un error amigable si no lo está."""
    if importlib.util.find_spec(module_name) is None:
        raise RuntimeError(
            f"El motor seleccionado ({db_name}) requiere el paquete opcional '{module_name}'. "
            f"Instálalo ejecutando: pip install 'asistpy[{package_extra}]'"
        )


class PersistenceFactory:
    """Fábrica para crear bundles de repositorios o repositorios individuales."""

    @classmethod
    def create_bundle(
        cls,
        backend: str | None = None,
        connection_string: str | None = None,
        init_tables: bool = True,
        **engine_kwargs: Any,
    ) -> PersistenceBundle:
        """Crea y entrega un conjunto completo de repositorios configurados."""
        resolved_backend = (
            backend
            or os.getenv("PERSISTENCE_BACKEND")
            or os.getenv("DB_ENGINE")
            or "memory"
        ).lower()

        if resolved_backend in ("memory", "inmemory", "test"):
            return PersistenceBundle(
                attendance_repo=InMemoryAttendanceRepository(),
                daily_attendance_repo=InMemoryDailyAttendanceRepository(),
                employee_repo=InMemoryEmployeeRepository(),
                branch_repo=InMemoryBranchRepository(),
                incidence_repo=InMemoryIncidenceRepository(),
                schedule_assignment_repo=InMemoryScheduleAssignmentRepository(),
                audit_repo=InMemoryAuditLogRepository(),
                sync_state_repo=InMemorySyncStateRepository(),
                device_repo=InMemoryDeviceRepository(),
                shift_repo=InMemoryShiftRepository(),
                rotation_pattern_repo=InMemoryRotationPatternRepository(),
                database=None,
            )

        # Configuración para bases de datos relacionales con SQLAlchemy
        resolved_url = connection_string or os.getenv("DATABASE_URL")
        if not resolved_url:
            if resolved_backend == "sqlite":
                resolved_url = "sqlite:///asistpy.db"
            else:
                raise ValueError(
                    f"Se seleccionó el backend relacional '{resolved_backend}' pero no se proporcionó "
                    f"connection_string ni la variable de entorno DATABASE_URL."
                )

        # Validación proactiva de drivers según la URL o backend
        if "postgres" in resolved_backend or resolved_url.startswith("postgresql"):
            check_driver_installed("psycopg", "postgres", "PostgreSQL")
        elif "mysql" in resolved_backend or resolved_url.startswith("mysql"):
            check_driver_installed("pymysql", "mysql", "MySQL")
        elif "sqlserver" in resolved_backend or "mssql" in resolved_backend or resolved_url.startswith("mssql"):
            check_driver_installed("pyodbc", "sqlserver", "SQL Server")
        elif "mongo" in resolved_backend or resolved_url.startswith("mongodb"):
            check_driver_installed("pymongo", "mongo", "MongoDB")
            # En caso de mongo, se instanciaría la suite de repositorios NoSQL
            raise NotImplementedError(
                "La suite de repositorios de MongoDB se implementará en la siguiente fase de NoSQL."
            )

        # Crear y preparar Database
        db = Database(resolved_url, **engine_kwargs)
        if init_tables:
            db.init_tables()

        session_factory = db.session_factory

        return PersistenceBundle(
            attendance_repo=SqlAttendanceRepository(session_factory),
            daily_attendance_repo=SqlDailyAttendanceRepository(session_factory),
            employee_repo=SqlEmployeeRepository(session_factory),
            branch_repo=SqlBranchRepository(session_factory),
            incidence_repo=SqlIncidenceRepository(session_factory),
            schedule_assignment_repo=SqlScheduleAssignmentRepository(session_factory),
            audit_repo=SqlAuditLogRepository(session_factory),
            sync_state_repo=SqlSyncStateRepository(session_factory),
            device_repo=SqlDeviceRepository(session_factory),
            shift_repo=SqlShiftRepository(session_factory),
            rotation_pattern_repo=SqlRotationPatternRepository(session_factory),
            database=db,
        )

    @classmethod
    def create_sql_bundle_from_session_factory(
        cls, session_factory: sessionmaker[Session]
    ) -> PersistenceBundle:
        """Permite crear un bundle reutilizando una session_factory existente (ej. pruebas unitarias)."""
        return PersistenceBundle(
            attendance_repo=SqlAttendanceRepository(session_factory),
            daily_attendance_repo=SqlDailyAttendanceRepository(session_factory),
            employee_repo=SqlEmployeeRepository(session_factory),
            branch_repo=SqlBranchRepository(session_factory),
            incidence_repo=SqlIncidenceRepository(session_factory),
            schedule_assignment_repo=SqlScheduleAssignmentRepository(session_factory),
            audit_repo=SqlAuditLogRepository(session_factory),
            sync_state_repo=SqlSyncStateRepository(session_factory),
            device_repo=SqlDeviceRepository(session_factory),
            shift_repo=SqlShiftRepository(session_factory),
            rotation_pattern_repo=SqlRotationPatternRepository(session_factory),
            database=None,
        )



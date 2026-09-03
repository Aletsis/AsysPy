"""Caso de uso central ProcessDailyAttendance y ProcessEmployeeAttendanceRange.

Orquesta el flujo completo de asistencia:
1. Resolver turno esperado con ScheduleResolver.
2. Obtener marcaciones del empleado desde AttendanceRepository.
3. Emparejar con SessionPairer.
4. Evaluar jornada con AttendanceEvaluator.
5. Guardar DailyAttendance en DailyAttendanceRepository.
6. Marcar logs como procesados en AttendanceRepository.
"""

from datetime import date, datetime, time, timedelta
from typing import Sequence

from attendance.domain.attendance import AttendanceEvaluator, DailyAttendance, SessionPairer
from attendance.domain.policy.overtime import OvertimePolicy
from attendance.domain.schedule import (
    RotationPattern,
    ScheduleException,
    ScheduleResolver,
    ShiftDefinition,
)
from attendance.ports.attendance import (
    AttendanceRepository,
    DailyAttendanceRepository,
)
from attendance.ports.incidence import IncidenceRepository
from attendance.ports.organization import EmployeeRepository
from attendance.ports.schedule import (
    EmployeeScheduleAssignmentRepository,
    RotationPatternRepository,
    ShiftRepository,
)


class ProcessDailyAttendance:
    """Caso de uso orquestador para procesar la jornada diaria de un empleado."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        daily_attendance_repo: DailyAttendanceRepository,
        schedule_assignment_repo: EmployeeScheduleAssignmentRepository,
        shift_definitions: dict[int, ShiftDefinition] | None = None,
        rotation_patterns: dict[int, RotationPattern] | None = None,
        schedule_exceptions: list[ScheduleException] | None = None,
        incidence_repo: IncidenceRepository | None = None,
        overtime_policy: OvertimePolicy | None = None,
        dedup_window_minutes: int = 2,
        shift_repo: ShiftRepository | None = None,
        rotation_pattern_repo: RotationPatternRepository | None = None,
    ) -> None:
        self.attendance_repo = attendance_repo
        self.daily_attendance_repo = daily_attendance_repo
        self.schedule_assignment_repo = schedule_assignment_repo
        self.shift_repo = shift_repo
        self.rotation_pattern_repo = rotation_pattern_repo

        if shift_definitions is not None:
            self.shift_definitions = dict(shift_definitions)
        elif self.shift_repo is not None:
            self.shift_definitions = {s.id: s for s in self.shift_repo.list_all()}
        else:
            self.shift_definitions = {}

        if rotation_patterns is not None:
            self.rotation_patterns = dict(rotation_patterns)
        elif self.rotation_pattern_repo is not None:
            self.rotation_patterns = {r.id: r for r in self.rotation_pattern_repo.list_all()}
        else:
            self.rotation_patterns = {}

        self.schedule_exceptions = schedule_exceptions or []
        self.incidence_repo = incidence_repo
        self.overtime_policy = overtime_policy
        self.dedup_window_minutes = dedup_window_minutes

    def execute(
        self,
        employee_pin: str,
        target_date: date,
        is_holiday: bool = False,
        mark_logs_processed: bool = True,
    ) -> DailyAttendance:
        """Orquesta la evaluación completa de la jornada de un empleado en una fecha operativa."""
        # 1. Resolver turno esperado con ScheduleResolver
        active_assignment = self.schedule_assignment_repo.get_active_assignment(
            employee_pin, as_of=target_date
        )

        shift_dict = dict(self.shift_definitions)
        rot_dict = dict(self.rotation_patterns)

        if active_assignment is not None:
            if (
                active_assignment.shift_definition_id is not None
                and active_assignment.shift_definition_id not in shift_dict
                and self.shift_repo is not None
            ):
                s = self.shift_repo.get_by_id(active_assignment.shift_definition_id)
                if s is not None:
                    shift_dict[s.id] = s
                    self.shift_definitions[s.id] = s

            if (
                active_assignment.rotation_pattern_id is not None
                and active_assignment.rotation_pattern_id not in rot_dict
                and self.rotation_pattern_repo is not None
            ):
                r = self.rotation_pattern_repo.get_by_id(active_assignment.rotation_pattern_id)
                if r is not None:
                    rot_dict[r.id] = r
                    self.rotation_patterns[r.id] = r
                    if self.shift_repo is not None:
                        for s_id in r.shift_sequence:
                            if s_id is not None and s_id not in shift_dict:
                                s = self.shift_repo.get_by_id(s_id)
                                if s is not None:
                                    shift_dict[s.id] = s
                                    self.shift_definitions[s.id] = s

        if self.shift_repo is not None:
            for exc in self.schedule_exceptions:
                if exc.shift_definition_id is not None and exc.shift_definition_id not in shift_dict:
                    s = self.shift_repo.get_by_id(exc.shift_definition_id)
                    if s is not None:
                        shift_dict[s.id] = s
                        self.shift_definitions[s.id] = s

        resolution = ScheduleResolver.resolve(
            employee_pin=employee_pin,
            target_date=target_date,
            exceptions=self.schedule_exceptions,
            active_assignment=active_assignment,
            shift_definitions=shift_dict,
            rotation_patterns=rot_dict,
        )

        # 2. Obtener marcaciones del empleado desde AttendanceRepository
        shift = resolution.shift_definition
        if shift is not None and shift.crosses_midnight:
            start_dt = datetime.combine(target_date, time.min)
            end_dt = datetime.combine(target_date + timedelta(days=1), time(12, 0))
            logs = self.attendance_repo.get_logs_for_employee(employee_pin, start_dt, end_dt)
        else:
            logs = self.attendance_repo.get_logs_by_employee_and_date(employee_pin, target_date)

        # 3. Emparejar marcaciones con SessionPairer
        sessions = SessionPairer.pair_logs(
            employee_pin=employee_pin,
            logs=logs,
            dedup_window_minutes=self.dedup_window_minutes,
        )

        # 4. Verificar si existe justificación previa aprobada (Incapacidad IMSS, Vacaciones, Permiso)
        justified_reason: str | None = None
        if self.incidence_repo is not None:
            justification = self.incidence_repo.get_active_justification(employee_pin, target_date)
            if justification is not None:
                doc_info = (
                    f" (Folio/Doc: {justification.support_document})"
                    if justification.support_document
                    else ""
                )
                justified_reason = (
                    f"[{justification.type.value.upper()}] {justification.reason}{doc_info}"
                )

        # 5. Evaluar jornada con AttendanceEvaluator
        daily_attendance = AttendanceEvaluator.evaluate_day(
            employee_pin=employee_pin,
            target_date=target_date,
            resolution=resolution,
            sessions=sessions,
            overtime_policy=self.overtime_policy,
            is_holiday=is_holiday,
            justified_absence_reason=justified_reason,
        )

        # 6. Guardar DailyAttendance
        saved_daily = self.daily_attendance_repo.save(daily_attendance)

        # 7. Marcar marcaciones como procesadas si corresponde
        if mark_logs_processed:
            for log in logs:
                if log.id is not None:
                    self.attendance_repo.mark_as_processed(log.id, inferred_type="daily_attendance")

        return saved_daily

    def __call__(
        self,
        employee_pin: str,
        target_date: date,
        is_holiday: bool = False,
        mark_logs_processed: bool = True,
    ) -> DailyAttendance:
        return self.execute(
            employee_pin=employee_pin,
            target_date=target_date,
            is_holiday=is_holiday,
            mark_logs_processed=mark_logs_processed,
        )


class ProcessEmployeeAttendanceRange:
    """Caso de uso orquestador para procesar la asistencia de un empleado en un rango de fechas."""

    def __init__(
        self,
        daily_processor: ProcessDailyAttendance | None = None,
        *,
        attendance_repo: AttendanceRepository | None = None,
        daily_attendance_repo: DailyAttendanceRepository | None = None,
        schedule_assignment_repo: EmployeeScheduleAssignmentRepository | None = None,
        shift_definitions: dict[int, ShiftDefinition] | None = None,
        rotation_patterns: dict[int, RotationPattern] | None = None,
        schedule_exceptions: list[ScheduleException] | None = None,
        incidence_repo: IncidenceRepository | None = None,
        overtime_policy: OvertimePolicy | None = None,
        dedup_window_minutes: int = 2,
        shift_repo: ShiftRepository | None = None,
        rotation_pattern_repo: RotationPatternRepository | None = None,
    ) -> None:
        if daily_processor is not None:
            self.daily_processor = daily_processor
        else:
            if (
                attendance_repo is None
                or daily_attendance_repo is None
                or schedule_assignment_repo is None
                or (shift_definitions is None and shift_repo is None)
                or (rotation_patterns is None and rotation_pattern_repo is None)
            ):
                raise ValueError(
                    "Debe proporcionarse daily_processor o todos los repositorios requeridos."
                )
            self.daily_processor = ProcessDailyAttendance(
                attendance_repo=attendance_repo,
                daily_attendance_repo=daily_attendance_repo,
                schedule_assignment_repo=schedule_assignment_repo,
                shift_definitions=shift_definitions,
                rotation_patterns=rotation_patterns,
                schedule_exceptions=schedule_exceptions,
                incidence_repo=incidence_repo,
                overtime_policy=overtime_policy,
                dedup_window_minutes=dedup_window_minutes,
                shift_repo=shift_repo,
                rotation_pattern_repo=rotation_pattern_repo,
            )

    def execute(
        self,
        employee_pin: str,
        start_date: date,
        end_date: date,
        holidays: Sequence[date] | set[date] | None = None,
        mark_logs_processed: bool = True,
    ) -> list[DailyAttendance]:
        if end_date < start_date:
            raise ValueError("end_date no puede ser anterior a start_date.")

        holiday_set = set(holidays or [])
        results: list[DailyAttendance] = []
        current_date = start_date

        while current_date <= end_date:
            is_holiday = current_date in holiday_set
            daily = self.daily_processor.execute(
                employee_pin=employee_pin,
                target_date=current_date,
                is_holiday=is_holiday,
                mark_logs_processed=mark_logs_processed,
            )
            results.append(daily)
            current_date += timedelta(days=1)

        return results

    def __call__(
        self,
        employee_pin: str,
        start_date: date,
        end_date: date,
        holidays: Sequence[date] | set[date] | None = None,
        mark_logs_processed: bool = True,
    ) -> list[DailyAttendance]:
        return self.execute(
            employee_pin=employee_pin,
            start_date=start_date,
            end_date=end_date,
            holidays=holidays,
            mark_logs_processed=mark_logs_processed,
        )


class ProcessDailyAttendanceBatch:
    """Caso de uso para procesar en lote la jornada de empleados activos."""

    def __init__(
        self,
        employee_repo: EmployeeRepository,
        daily_processor: ProcessDailyAttendance | None = None,
        *,
        attendance_repo: AttendanceRepository | None = None,
        daily_attendance_repo: DailyAttendanceRepository | None = None,
        schedule_assignment_repo: EmployeeScheduleAssignmentRepository | None = None,
        shift_definitions: dict[int, ShiftDefinition] | None = None,
        rotation_patterns: dict[int, RotationPattern] | None = None,
        schedule_exceptions: list[ScheduleException] | None = None,
        incidence_repo: IncidenceRepository | None = None,
        overtime_policy: OvertimePolicy | None = None,
        dedup_window_minutes: int = 2,
        shift_repo: ShiftRepository | None = None,
        rotation_pattern_repo: RotationPatternRepository | None = None,
    ) -> None:
        self.employee_repo = employee_repo
        if daily_processor is not None:
            self.daily_processor = daily_processor
        else:
            if (
                attendance_repo is None
                or daily_attendance_repo is None
                or schedule_assignment_repo is None
                or (shift_definitions is None and shift_repo is None)
                or (rotation_patterns is None and rotation_pattern_repo is None)
            ):
                raise ValueError(
                    "Debe proporcionarse daily_processor o todos los repositorios requeridos."
                )
            self.daily_processor = ProcessDailyAttendance(
                attendance_repo=attendance_repo,
                daily_attendance_repo=daily_attendance_repo,
                schedule_assignment_repo=schedule_assignment_repo,
                shift_definitions=shift_definitions,
                rotation_patterns=rotation_patterns,
                schedule_exceptions=schedule_exceptions,
                incidence_repo=incidence_repo,
                overtime_policy=overtime_policy,
                dedup_window_minutes=dedup_window_minutes,
                shift_repo=shift_repo,
                rotation_pattern_repo=rotation_pattern_repo,
            )

    def execute(
        self,
        target_date: date,
        branch_id: int | None = None,
        is_holiday: bool = False,
        mark_logs_processed: bool = True,
    ) -> list[DailyAttendance]:
        if hasattr(self.employee_repo, "get_active_employees"):
            active_employees = self.employee_repo.get_active_employees(branch_id=branch_id)
        else:
            active_employees = self.employee_repo.list_active(branch_id=branch_id)

        results: list[DailyAttendance] = []
        for employee in active_employees:
            daily = self.daily_processor.execute(
                employee_pin=employee.pin,
                target_date=target_date,
                is_holiday=is_holiday,
                mark_logs_processed=mark_logs_processed,
            )
            results.append(daily)

        return results

    def __call__(
        self,
        target_date: date,
        branch_id: int | None = None,
        is_holiday: bool = False,
        mark_logs_processed: bool = True,
    ) -> list[DailyAttendance]:
        return self.execute(
            target_date=target_date,
            branch_id=branch_id,
            is_holiday=is_holiday,
            mark_logs_processed=mark_logs_processed,
        )


def process_daily_attendance(
    employee_pin: str,
    target_date: date,
    attendance_repo: AttendanceRepository,
    daily_attendance_repo: DailyAttendanceRepository,
    schedule_assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definitions: dict[int, ShiftDefinition] | None = None,
    rotation_patterns: dict[int, RotationPattern] | None = None,
    schedule_exceptions: list[ScheduleException] | None = None,
    incidence_repo: IncidenceRepository | None = None,
    overtime_policy: OvertimePolicy | None = None,
    is_holiday: bool = False,
    dedup_window_minutes: int = 2,
    mark_logs_processed: bool = True,
    shift_repo: ShiftRepository | None = None,
    rotation_pattern_repo: RotationPatternRepository | None = None,
) -> DailyAttendance:
    """Función de conveniencia para procesar la jornada diaria de un empleado."""
    processor = ProcessDailyAttendance(
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_attendance_repo,
        schedule_assignment_repo=schedule_assignment_repo,
        shift_definitions=shift_definitions,
        rotation_patterns=rotation_patterns,
        schedule_exceptions=schedule_exceptions,
        incidence_repo=incidence_repo,
        overtime_policy=overtime_policy,
        dedup_window_minutes=dedup_window_minutes,
        shift_repo=shift_repo,
        rotation_pattern_repo=rotation_pattern_repo,
    )
    return processor.execute(
        employee_pin=employee_pin,
        target_date=target_date,
        is_holiday=is_holiday,
        mark_logs_processed=mark_logs_processed,
    )


def process_employee_attendance_range(
    employee_pin: str,
    start_date: date,
    end_date: date,
    attendance_repo: AttendanceRepository,
    daily_attendance_repo: DailyAttendanceRepository,
    schedule_assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definitions: dict[int, ShiftDefinition] | None = None,
    rotation_patterns: dict[int, RotationPattern] | None = None,
    schedule_exceptions: list[ScheduleException] | None = None,
    incidence_repo: IncidenceRepository | None = None,
    overtime_policy: OvertimePolicy | None = None,
    holidays: Sequence[date] | set[date] | None = None,
    dedup_window_minutes: int = 2,
    mark_logs_processed: bool = True,
    shift_repo: ShiftRepository | None = None,
    rotation_pattern_repo: RotationPatternRepository | None = None,
) -> list[DailyAttendance]:
    """Función de conveniencia para procesar la asistencia de un empleado en un rango de fechas."""
    range_processor = ProcessEmployeeAttendanceRange(
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_attendance_repo,
        schedule_assignment_repo=schedule_assignment_repo,
        shift_definitions=shift_definitions,
        rotation_patterns=rotation_patterns,
        schedule_exceptions=schedule_exceptions,
        incidence_repo=incidence_repo,
        overtime_policy=overtime_policy,
        dedup_window_minutes=dedup_window_minutes,
        shift_repo=shift_repo,
        rotation_pattern_repo=rotation_pattern_repo,
    )
    return range_processor.execute(
        employee_pin=employee_pin,
        start_date=start_date,
        end_date=end_date,
        holidays=holidays,
        mark_logs_processed=mark_logs_processed,
    )


def process_daily_attendance_batch(
    target_date: date,
    employee_repo: EmployeeRepository,
    attendance_repo: AttendanceRepository,
    daily_attendance_repo: DailyAttendanceRepository,
    schedule_assignment_repo: EmployeeScheduleAssignmentRepository,
    shift_definitions: dict[int, ShiftDefinition] | None = None,
    rotation_patterns: dict[int, RotationPattern] | None = None,
    branch_id: int | None = None,
    schedule_exceptions: list[ScheduleException] | None = None,
    incidence_repo: IncidenceRepository | None = None,
    overtime_policy: OvertimePolicy | None = None,
    is_holiday: bool = False,
    dedup_window_minutes: int = 2,
    mark_logs_processed: bool = True,
    shift_repo: ShiftRepository | None = None,
    rotation_pattern_repo: RotationPatternRepository | None = None,
) -> list[DailyAttendance]:
    """Función de conveniencia para procesar en lote la jornada de empleados activos."""
    batch_processor = ProcessDailyAttendanceBatch(
        employee_repo=employee_repo,
        attendance_repo=attendance_repo,
        daily_attendance_repo=daily_attendance_repo,
        schedule_assignment_repo=schedule_assignment_repo,
        shift_definitions=shift_definitions,
        rotation_patterns=rotation_patterns,
        schedule_exceptions=schedule_exceptions,
        incidence_repo=incidence_repo,
        overtime_policy=overtime_policy,
        dedup_window_minutes=dedup_window_minutes,
        shift_repo=shift_repo,
        rotation_pattern_repo=rotation_pattern_repo,
    )
    return batch_processor.execute(
        target_date=target_date,
        branch_id=branch_id,
        is_holiday=is_holiday,
        mark_logs_processed=mark_logs_processed,
    )


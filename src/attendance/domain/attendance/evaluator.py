"""Servicio de dominio AttendanceEvaluator para calcular métricas de jornada diaria."""

from datetime import date, datetime, timedelta

from attendance.domain.policy.overtime import OvertimePolicy
from attendance.domain.schedule.enums import ScheduleKind
from attendance.domain.schedule.resolver import ScheduleResolution

from .daily_attendance import DailyAttendance
from .enums import AttendanceStatus
from .session import WorkSession


class AttendanceEvaluator:
    """Servicio de Dominio que evalúa la asistencia diaria de un empleado contra su horario esperado y políticas."""

    @classmethod
    def evaluate_day(
        cls,
        employee_pin: str,
        target_date: date,
        resolution: ScheduleResolution,
        sessions: list[WorkSession],
        overtime_policy: OvertimePolicy | None = None,
        is_holiday: bool = False,
        justified_absence_reason: str | None = None,
    ) -> DailyAttendance:
        # 1. Justificación formal previa (Incapacidad, Vacaciones, Permiso especial)
        if justified_absence_reason is not None and not sessions:
            return DailyAttendance(
                employee_pin=employee_pin,
                date=target_date,
                expected_shift=resolution.shift_definition,
                sessions=[],
                status=AttendanceStatus.JUSTIFIED_ABSENCE,
                notes=justified_absence_reason,
            )

        # 2. Feriado / Festivo oficial
        if is_holiday:
            if not sessions:
                return DailyAttendance(
                    employee_pin=employee_pin,
                    date=target_date,
                    expected_shift=resolution.shift_definition,
                    sessions=[],
                    status=AttendanceStatus.HOLIDAY,
                )
            # Laboró en día festivo
            daily = DailyAttendance(
                employee_pin=employee_pin,
                date=target_date,
                expected_shift=resolution.shift_definition,
                sessions=sessions,
                status=AttendanceStatus.PRESENT,
                notes="Laboró en día festivo oficial",
            )
            if overtime_policy and overtime_policy.overtime_allowed:
                daily.overtime_minutes = overtime_policy.calculate_effective_overtime(
                    daily.total_worked_minutes
                )
            return daily

        # 3. Día de Descanso Programado (OFF)
        if resolution.kind == ScheduleKind.OFF:
            if not sessions:
                return DailyAttendance(
                    employee_pin=employee_pin,
                    date=target_date,
                    expected_shift=None,
                    sessions=[],
                    status=AttendanceStatus.REST_DAY,
                )
            # Laboró en su día de descanso semanal
            daily = DailyAttendance(
                employee_pin=employee_pin,
                date=target_date,
                expected_shift=None,
                sessions=sessions,
                status=AttendanceStatus.PRESENT,
                notes="Laboró en día de descanso",
            )
            if overtime_policy and overtime_policy.overtime_allowed:
                daily.overtime_minutes = overtime_policy.calculate_effective_overtime(
                    daily.total_worked_minutes
                )
            return daily

        # 4. Turno Fijo Programado
        shift = resolution.shift_definition
        if resolution.kind == ScheduleKind.FIXED and shift is not None:
            if not sessions:
                return DailyAttendance(
                    employee_pin=employee_pin,
                    date=target_date,
                    expected_shift=shift,
                    sessions=[],
                    status=AttendanceStatus.ABSENT,
                )

            daily = DailyAttendance(
                employee_pin=employee_pin,
                date=target_date,
                expected_shift=shift,
                sessions=sessions,
            )

            # Evaluar Retardo (Tardiness) en la entrada
            if daily.first_check_in is not None and shift.start_time is not None:
                expected_start_dt = datetime.combine(target_date, shift.start_time)
                tolerance_dt = expected_start_dt + timedelta(minutes=shift.tolerance_minutes)
                if daily.first_check_in > tolerance_dt:
                    diff_seconds = (daily.first_check_in - expected_start_dt).total_seconds()
                    daily.tardiness_minutes = max(0, int(diff_seconds // 60))

            # Evaluar Salida Anticipada (Early Departure)
            if daily.last_check_out is not None and shift.end_time is not None:
                end_date = (
                    target_date + timedelta(days=1) if shift.crosses_midnight else target_date
                )
                expected_end_dt = datetime.combine(end_date, shift.end_time)
                if daily.last_check_out < expected_end_dt:
                    diff_seconds = (expected_end_dt - daily.last_check_out).total_seconds()
                    daily.early_departure_minutes = max(0, int(diff_seconds // 60))

            # Evaluar Horas Extras
            if overtime_policy and overtime_policy.overtime_allowed:
                expected_work = shift.expected_work_minutes
                if daily.total_worked_minutes > expected_work:
                    raw_overtime = daily.total_worked_minutes - expected_work
                    daily.overtime_minutes = overtime_policy.calculate_effective_overtime(
                        raw_overtime
                    )

            # Determinar Estatus General
            if daily.has_open_sessions:
                daily.status = AttendanceStatus.INCOMPLETE
            elif daily.tardiness_minutes > 0:
                daily.status = AttendanceStatus.LATE
            elif daily.early_departure_minutes > 0:
                daily.status = AttendanceStatus.EARLY_DEPARTURE
            else:
                daily.status = AttendanceStatus.PRESENT

            return daily

        # 5. Esquema Abierto / Flexible
        if not sessions:
            return DailyAttendance(
                employee_pin=employee_pin,
                date=target_date,
                expected_shift=None,
                sessions=[],
                status=AttendanceStatus.ABSENT,
            )

        daily = DailyAttendance(
            employee_pin=employee_pin,
            date=target_date,
            expected_shift=None,
            sessions=sessions,
            status=AttendanceStatus.INCOMPLETE
            if any(s.is_open for s in sessions)
            else AttendanceStatus.PRESENT,
        )
        return daily

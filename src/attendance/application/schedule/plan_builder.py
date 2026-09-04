"""Constructor y generador de planes de horario para empleados.

Permite orquestar turnos fijos o rotativos combinados con esquemas de descanso:
- Descanso semanal fijo (ej. domingos, sábados y domingos).
- Descanso rotativo escalonado / rolado (se recorre al día siguiente cada N semanas).
- Descanso rotativo alternado (alterna entre días predefinidos).
- Ciclos continuos de trabajo x descanso (ej. 6x1, 4x2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from attendance.domain.common.exceptions import ValidationError
from attendance.domain.schedule.assignment import EmployeeScheduleAssignment
from attendance.domain.schedule.enums import AssignmentMode, RotationFrequency, Weekday
from attendance.domain.schedule.rotation import RotationPattern
from attendance.domain.schedule.shift import ShiftDefinition


class ShiftModeOption(str, Enum):
    FIXED = "fixed"
    ROTATING = "rotating"


class RestModeOption(str, Enum):
    FIXED = "fixed"
    ROLLING = "rolling"          # Se recorre al siguiente día
    ALTERNATING = "alternating"  # Alterna entre días fijos (ej. sem 1 dom, sem 2 sab)
    WORK_REST_CYCLE = "cycle"    # N laborados x M descansos (ej. 6x1, 4x2)


@dataclass
class DaySchedulePreview:
    """Detalle de un día en la previsualización del horario."""

    date: date
    day_name: str
    shift_id: int | None
    shift_name: str
    is_rest_day: bool
    time_range_str: str


@dataclass
class SchedulePlanConfig:
    """Configuración integral seleccionada por el usuario en la GUI o CLI."""

    employee_pin: str
    valid_from: date
    valid_until: date | None = None

    # Esquema de turnos
    shift_mode: ShiftModeOption = ShiftModeOption.FIXED
    fixed_shift_id: int | None = None
    rotating_shift_ids: list[int] | None = None
    shift_frequency_weeks: int = 1  # Cada cuántas semanas rota el turno

    # Esquema de descansos
    rest_mode: RestModeOption = RestModeOption.FIXED

    # RestModeOption.FIXED: conjunto de días de descanso (0=Lunes, ..., 6=Domingo)
    fixed_rest_weekdays: set[int] | None = None

    # RestModeOption.ROLLING:
    rolling_initial_weekday: int = 6   # Día en que empieza descansando (6=Domingo)
    rolling_interval_weeks: int = 1    # Cada cuántas semanas se recorre (ej. 1=semanal, 2=quincenal)
    rolling_step_days: int = 1         # Cuántos días se desplaza (+1 hacia adelante)

    # RestModeOption.ALTERNATING:
    alternating_rest_weekdays: list[int] | None = None  # ej. [6, 5] = dom, sab
    alternating_interval_weeks: int = 1

    # RestModeOption.WORK_REST_CYCLE:
    cycle_work_days: int = 6
    cycle_rest_days: int = 1


WEEKDAY_SPANISH = [
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
]


def _lcm(a: int, b: int) -> int:
    """Calcula el mínimo común múltiplo entre dos enteros positivos."""
    if a <= 0 or b <= 0:
        return max(a, b, 1)
    return abs(a * b) // math.gcd(a, b)


class SchedulePlanBuilder:
    """Servicio de aplicación para componer, previsualizar y generar asignaciones y patrones."""

    @classmethod
    def validate_config(
        cls,
        config: SchedulePlanConfig,
        shifts: dict[int, ShiftDefinition],
    ) -> None:
        """Valida que la configuración sea consistente y que los turnos existan."""
        if not config.employee_pin.strip():
            raise ValidationError("Debe especificar el colaborador.")

        if config.valid_until and config.valid_until < config.valid_from:
            raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio.")

        # Validar turnos
        if config.shift_mode == ShiftModeOption.FIXED:
            if config.fixed_shift_id is None:
                raise ValidationError("Debe seleccionar un turno fijo.")
            if config.fixed_shift_id not in shifts:
                raise ValidationError(f"Turno con ID {config.fixed_shift_id} no existe.")
        else:
            if not config.rotating_shift_ids:
                raise ValidationError("Debe seleccionar al menos un turno para la rotación.")
            for sid in config.rotating_shift_ids:
                if sid not in shifts:
                    raise ValidationError(f"Turno con ID {sid} no existe.")

        # Validar descansos
        if config.rest_mode == RestModeOption.FIXED:
            if config.fixed_rest_weekdays is None or len(config.fixed_rest_weekdays) == 0:
                raise ValidationError("Debe seleccionar al menos un día de descanso.")
            if len(config.fixed_rest_weekdays) >= 7:
                raise ValidationError("No se pueden marcar los 7 días de la semana como descanso.")

        elif config.rest_mode == RestModeOption.ROLLING:
            if not 0 <= config.rolling_initial_weekday <= 6:
                raise ValidationError("El día inicial de descanso debe ser de Lunes a Domingo.")
            if config.rolling_interval_weeks < 1:
                raise ValidationError("El intervalo de semanas para recorrer el descanso debe ser >= 1.")

        elif config.rest_mode == RestModeOption.ALTERNATING:
            if not config.alternating_rest_weekdays:
                raise ValidationError("Debe definir los días de descanso a alternar.")
            if config.alternating_interval_weeks < 1:
                raise ValidationError("El intervalo de alternancia debe ser >= 1 semana.")

        elif config.rest_mode == RestModeOption.WORK_REST_CYCLE:
            if config.cycle_work_days < 1:
                raise ValidationError("Los días continuos de trabajo deben ser al menos 1.")
            if config.cycle_rest_days < 1:
                raise ValidationError("Los días continuos de descanso deben ser al menos 1.")

    @classmethod
    def resolve_day_schedule(
        cls,
        target_date: date,
        config: SchedulePlanConfig,
        shifts: dict[int, ShiftDefinition],
    ) -> tuple[int | None, bool]:
        """Resuelve el turno y si es descanso para una fecha dada.

        Retorna (shift_id, is_rest_day). Si es descanso, shift_id es None.
        """
        # 1. Determinar si es día de descanso
        is_rest = False

        if config.rest_mode == RestModeOption.FIXED:
            rest_days = config.fixed_rest_weekdays or {6}
            is_rest = target_date.weekday() in rest_days

        elif config.rest_mode == RestModeOption.ROLLING:
            # Ancla es el lunes de la semana de valid_from
            anchor_monday = config.valid_from - timedelta(days=config.valid_from.weekday())
            days_from_anchor = (target_date - anchor_monday).days
            week_idx = days_from_anchor // 7
            interval = max(1, config.rolling_interval_weeks)
            shift_count = week_idx // interval
            rest_weekday = (config.rolling_initial_weekday + shift_count * config.rolling_step_days) % 7
            is_rest = target_date.weekday() == rest_weekday

        elif config.rest_mode == RestModeOption.ALTERNATING:
            alt_list = config.alternating_rest_weekdays or [6]
            anchor_monday = config.valid_from - timedelta(days=config.valid_from.weekday())
            days_from_anchor = (target_date - anchor_monday).days
            week_idx = days_from_anchor // 7
            interval = max(1, config.alternating_interval_weeks)
            alt_idx = (week_idx // interval) % len(alt_list)
            is_rest = target_date.weekday() == alt_list[alt_idx]

        elif config.rest_mode == RestModeOption.WORK_REST_CYCLE:
            total_cycle = config.cycle_work_days + config.cycle_rest_days
            days_from_start = (target_date - config.valid_from).days
            pos = days_from_start % total_cycle
            is_rest = pos >= config.cycle_work_days

        if is_rest:
            return None, True

        # 2. Si no es descanso, determinar qué turno corresponde
        if config.shift_mode == ShiftModeOption.FIXED:
            return config.fixed_shift_id, False

        # Turno rotativo
        rot_shifts = config.rotating_shift_ids or [config.fixed_shift_id or 1]
        anchor_monday = config.valid_from - timedelta(days=config.valid_from.weekday())
        days_from_anchor = (target_date - anchor_monday).days
        week_idx = days_from_anchor // 7
        interval = max(1, config.shift_frequency_weeks)
        shift_idx = (week_idx // interval) % len(rot_shifts)
        return rot_shifts[shift_idx], False

    @classmethod
    def generate_preview(
        cls,
        config: SchedulePlanConfig,
        shifts: dict[int, ShiftDefinition],
        days: int = 30,
    ) -> list[DaySchedulePreview]:
        """Genera la lista de previsualización día por día para los próximos N días."""
        cls.validate_config(config, shifts)
        preview_list: list[DaySchedulePreview] = []

        current_date = config.valid_from
        for _ in range(days):
            shift_id, is_rest = cls.resolve_day_schedule(current_date, config, shifts)
            day_name = WEEKDAY_SPANISH[current_date.weekday()]

            if is_rest or shift_id is None:
                shift_name = "Descanso"
                time_range = "Día Libre (OFF)"
            else:
                sh = shifts.get(shift_id)
                if sh:
                    shift_name = sh.name
                    time_range = f"{sh.start_time.strftime('%H:%M')} - {sh.end_time.strftime('%H:%M')}"
                else:
                    shift_name = f"Turno #{shift_id}"
                    time_range = "N/A"

            preview_list.append(
                DaySchedulePreview(
                    date=current_date,
                    day_name=day_name,
                    shift_id=shift_id,
                    shift_name=shift_name,
                    is_rest_day=is_rest,
                    time_range_str=time_range,
                )
            )
            current_date += timedelta(days=1)

        return preview_list

    @classmethod
    def build_assignment_and_pattern(
        cls,
        config: SchedulePlanConfig,
        shifts: dict[int, ShiftDefinition],
        pattern_name_prefix: str = "Rol Automático",
    ) -> tuple[EmployeeScheduleAssignment, RotationPattern | None]:
        """Construye las entidades listas para guardar en los repositorios."""
        cls.validate_config(config, shifts)

        # Caso simple: Turno Fijo + Descanso Fijo semanal
        if config.shift_mode == ShiftModeOption.FIXED and config.rest_mode == RestModeOption.FIXED:
            rest_weekdays = config.fixed_rest_weekdays or {6}
            work_weekdays = {Weekday(w) for w in range(7) if w not in rest_weekdays}
            assignment = EmployeeScheduleAssignment(
                id=None,
                employee_pin=config.employee_pin,
                mode=AssignmentMode.FIXED,
                valid_from=config.valid_from,
                valid_until=config.valid_until,
                working_weekdays=work_weekdays,
                shift_definition_id=config.fixed_shift_id,
                rotation_pattern_id=None,
            )
            return assignment, None

        # Casos rotativos: construir un RotationPattern de frecuencia diaria
        if config.rest_mode == RestModeOption.WORK_REST_CYCLE:
            # Ciclo continuo NxM
            anchor_date = config.valid_from
            total_cycle = config.cycle_work_days + config.cycle_rest_days
            shift_seq: list[int | None] = []
            for d in range(total_cycle):
                dt = anchor_date + timedelta(days=d)
                sid, is_rest = cls.resolve_day_schedule(dt, config, shifts)
                shift_seq.append(None if is_rest else sid)

            pattern = RotationPattern(
                id=None,
                name=f"{pattern_name_prefix} ({config.cycle_work_days}x{config.cycle_rest_days})",
                shift_sequence=shift_seq,
                frequency=RotationFrequency.DAILY,
                anchor_date=anchor_date,
            )
        else:
            # Esquemas basados en semanas (Rolling, Alternating, o Turnos Rotativos)
            anchor_date = config.valid_from - timedelta(days=config.valid_from.weekday())

            # Calcular duración del ciclo en semanas
            weeks_shift = (
                len(config.rotating_shift_ids or [1]) * max(1, config.shift_frequency_weeks)
                if config.shift_mode == ShiftModeOption.ROTATING
                else 1
            )

            if config.rest_mode == RestModeOption.ROLLING:
                # 7 desplazamientos de descanso * intervalo
                weeks_rest = 7 * max(1, config.rolling_interval_weeks)
            elif config.rest_mode == RestModeOption.ALTERNATING:
                weeks_rest = len(config.alternating_rest_weekdays or [1]) * max(1, config.alternating_interval_weeks)
            else:
                weeks_rest = 1

            total_weeks = _lcm(weeks_shift, weeks_rest)
            # Limitar ciclo máximo a un año (52 semanas) para evitar secuencias excesivamente grandes
            total_weeks = min(total_weeks, 52)
            total_days = total_weeks * 7

            shift_seq = []
            for d in range(total_days):
                dt = anchor_date + timedelta(days=d)
                sid, is_rest = cls.resolve_day_schedule(dt, config, shifts)
                shift_seq.append(None if is_rest else sid)

            desc = "Descanso Rolado" if config.rest_mode == RestModeOption.ROLLING else "Turno Rotativo"
            pattern = RotationPattern(
                id=None,
                name=f"{pattern_name_prefix} ({desc} {total_weeks} sem)",
                shift_sequence=shift_seq,
                frequency=RotationFrequency.DAILY,
                anchor_date=anchor_date,
            )

        assignment = EmployeeScheduleAssignment(
            id=None,
            employee_pin=config.employee_pin,
            mode=AssignmentMode.ROTATING,
            valid_from=config.valid_from,
            valid_until=config.valid_until,
            working_weekdays=None,  # La secuencia diaria del patrón ya determina exactamente los descansos
            shift_definition_id=None,
            rotation_pattern_id=None,  # Se asignará tras persistir el patrón
        )
        return assignment, pattern

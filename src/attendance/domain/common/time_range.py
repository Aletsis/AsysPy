"""Value Object TimeRange para representar rangos horarios con soporte para cruce de medianoche."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .exceptions import TimeRangeError


@dataclass(frozen=True)
class TimeRange:
    """Rango de horas dentro de un turno o jornada.

    Soporta turnos diurnos (ej. 08:00 a 17:00) y turnos nocturnos
    que cruzan la medianoche (ej. 22:00 a 06:00).
    """

    start_time: time
    end_time: time
    crosses_midnight: bool = False

    def __post_init__(self) -> None:
        if self.start_time == self.end_time:
            raise TimeRangeError("La hora de inicio y fin no pueden ser idénticas.")

        inferred_crosses = self.end_time < self.start_time
        # Si se especificó explícitamente False pero end_time < start_time, corregimos o validamos
        if inferred_crosses and not self.crosses_midnight:
            # En dataclass frozen usamos object.__setattr__
            object.__setattr__(self, "crosses_midnight", True)
        elif not inferred_crosses and self.crosses_midnight:
            raise TimeRangeError(
                f"crosses_midnight es True pero end_time ({self.end_time}) es mayor que start_time ({self.start_time})."
            )

    @property
    def duration_minutes(self) -> int:
        """Duración total del rango en minutos."""
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        if not self.crosses_midnight:
            return end_min - start_min
        return (1440 - start_min) + end_min

    def to_datetimes(self, base_date: date) -> tuple[datetime, datetime]:
        """Convierte las horas a datetimes ancladas a una fecha base (inicio de jornada)."""
        start_dt = datetime.combine(base_date, self.start_time)
        end_date = base_date + timedelta(days=1) if self.crosses_midnight else base_date
        end_dt = datetime.combine(end_date, self.end_time)
        return start_dt, end_dt

    def contains_datetime(self, dt: datetime, base_date: date) -> bool:
        """Verifica si un datetime cae dentro del rango para la fecha base dada."""
        start_dt, end_dt = self.to_datetimes(base_date)
        return start_dt <= dt <= end_dt

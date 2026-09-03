"""Enums para sesiones de trabajo y estado de asistencia diaria."""

from enum import Enum


class SessionType(str, Enum):
    REGULAR_WORK = "regular_work"  # Turno de trabajo ordinario
    SPLIT_SHIFT_PART = "split_shift_part"  # Parte de un turno partido (mañana o tarde)
    MEAL_BREAK = "meal_break"  # Pausa de comida
    PERMISSION = "permission"  # Salida con permiso/pase dentro de jornada
    OTHER = "other"  # Otras incidencias


class SessionStatus(str, Enum):
    CLOSED = "closed"  # Tiene entrada y salida válidas
    OPEN = "open"  # Solo tiene entrada, pendiente de checar salida
    SUSPICIOUS = "suspicious"  # Secuencia anómala o inconsistente


class AttendanceStatus(str, Enum):
    PRESENT = "present"  # Asistencia completa dentro de parámetros
    LATE = "late"  # Asistencia con retardo (superó tolerancia)
    EARLY_DEPARTURE = "early_departure"  # Salida anticipada sin justificar
    INCOMPLETE = "incomplete"  # Falta marcación de entrada o salida
    ABSENT = "absent"  # Falta injustificada (no se presentó a laborar)
    JUSTIFIED_ABSENCE = "justified_absence"  # Permiso, vacaciones o incapacidad médica
    REST_DAY = "rest_day"  # Día de descanso semanal
    HOLIDAY = "holiday"  # Día feriado oficial / festivo

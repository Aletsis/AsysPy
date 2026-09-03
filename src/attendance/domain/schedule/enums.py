"""Enums para el subdominio de horarios y turnos."""

from enum import Enum


class ShiftCategory(str, Enum):
    MATUTINO = "matutino"
    VESPERTINO = "vespertino"
    NOCTURNO = "nocturno"
    MIXTO = "mixto"
    PERSONALIZADO = "personalizado"


class RotationFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class AssignmentMode(str, Enum):
    FIXED = "fixed"
    ROTATING = "rotating"
    OPEN = "open"


class ScheduleKind(str, Enum):
    OFF = "off"
    FIXED = "fixed"
    OPEN = "open"


class Weekday(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

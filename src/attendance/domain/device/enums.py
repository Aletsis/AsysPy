"""Enums para dispositivos biométricos y telemetría de marcaciones."""

from enum import Enum


class DeviceProtocol(str, Enum):
    TCP_4370 = "tcp_4370"
    ADMS = "adms"


class AuthMethod(str, Enum):
    PASSWORD = "password"  # punch = 0
    FINGERPRINT = "fingerprint"  # punch = 1
    CARD = "card"  # punch = 2 o 3
    FACE = "face"  # punch = 4 o 15
    MANUAL = "manual"  # ajuste manual administrativo
    UNKNOWN = "unknown"

    @classmethod
    def from_punch_code(cls, punch: int) -> "AuthMethod":
        mapping = {
            0: cls.PASSWORD,
            1: cls.FINGERPRINT,
            2: cls.CARD,
            3: cls.CARD,
            4: cls.FACE,
            15: cls.FACE,
        }
        return mapping.get(punch, cls.UNKNOWN)


class LogStatus(str, Enum):
    RAW = "raw"  # tal como llegó del reloj, sin procesar
    PROCESSED = "processed"  # ya se emparejó o evaluó en una sesión de trabajo
    IGNORED = "ignored"  # descartado (ej. duplicado dentro de ventana de tolerancia)

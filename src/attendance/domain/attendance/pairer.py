"""Servicio de dominio SessionPairer para deduplicación y emparejamiento de marcaciones."""

from datetime import timedelta

from attendance.domain.device.log import AttendanceLog

from .enums import SessionStatus, SessionType
from .session import WorkSession


class SessionPairer:
    """Servicio de Dominio para deduplicar marcaciones y emparejarlas en sesiones IN/OUT."""

    @staticmethod
    def deduplicate(
        logs: list[AttendanceLog],
        window_minutes: int = 2,
    ) -> list[AttendanceLog]:
        """Descarta marcaciones consecutivas dentro de una ventana de tolerancia (doble toque accidental)."""
        if not logs:
            return []

        sorted_logs = sorted(logs, key=lambda log: log.timestamp)
        deduped = [sorted_logs[0]]

        window = timedelta(minutes=window_minutes)
        for log in sorted_logs[1:]:
            last = deduped[-1]
            if (log.timestamp - last.timestamp) < window:
                continue
            deduped.append(log)

        return deduped

    @classmethod
    def pair_logs(
        cls,
        employee_pin: str,
        logs: list[AttendanceLog],
        dedup_window_minutes: int = 2,
        default_session_type: SessionType = SessionType.REGULAR_WORK,
    ) -> list[WorkSession]:
        """Empareja las marcaciones ordenadas de un empleado en sesiones IN/OUT."""
        deduped = cls.deduplicate(logs, window_minutes=dedup_window_minutes)
        sessions: list[WorkSession] = []

        i = 0
        while i < len(deduped):
            check_in_log = deduped[i]

            if i + 1 < len(deduped):
                check_out_log = deduped[i + 1]
                sessions.append(
                    WorkSession(
                        id=None,
                        employee_pin=employee_pin,
                        check_in=check_in_log.timestamp,
                        check_out=check_out_log.timestamp,
                        check_in_log_id=check_in_log.id,
                        check_out_log_id=check_out_log.id,
                        check_in_device_id=check_in_log.device_id,
                        check_out_device_id=check_out_log.device_id,
                        session_type=default_session_type,
                        status=SessionStatus.CLOSED,
                    )
                )
                i += 2
            else:
                # Marcación impar al final: sesión abierta
                sessions.append(
                    WorkSession(
                        id=None,
                        employee_pin=employee_pin,
                        check_in=check_in_log.timestamp,
                        check_out=None,
                        check_in_log_id=check_in_log.id,
                        check_out_log_id=None,
                        check_in_device_id=check_in_log.device_id,
                        check_out_device_id=None,
                        session_type=default_session_type,
                        status=SessionStatus.OPEN,
                    )
                )
                i += 1

        return sessions

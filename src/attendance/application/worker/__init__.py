"""Módulo de servicio y demonio en segundo plano (worker) para AsistPy."""

from .daemon import AttendanceWorker

__all__ = ["AttendanceWorker"]

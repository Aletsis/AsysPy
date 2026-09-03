"""Gestión de configuración para la interfaz gráfica de AsistPy."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DesktopConfig:
    backend: str = "sqlite"
    database_url: str = "sqlite:///asistpy.db"
    first_run_completed: bool = False
    last_branch: str | None = None
    theme: str = "dark"

    @property
    def is_sqlite(self) -> bool:
        return self.backend.lower() in ("sqlite", "sqlite3")


class ConfigManager:
    """Administra la carga, detección y persistencia de configuración para la GUI."""

    def __init__(self, env_path: str | Path | None = None) -> None:
        self.env_path = Path(env_path) if env_path else Path(".env")

    def is_first_run(self) -> bool:
        """Determina si la aplicación se ejecuta por primera vez sin configuración previa."""
        if not self.env_path.exists():
            return True

        backend = os.getenv("PERSISTENCE_BACKEND") or os.getenv("DB_ENGINE")
        db_url = os.getenv("DATABASE_URL")

        if not backend and not db_url:
            # Si el archivo .env existe pero está vacío o sin base de datos configurada
            config = self.load()
            if not config.backend or not config.database_url:
                return True

        return False

    def load(self) -> DesktopConfig:
        """Carga la configuración desde el archivo .env si existe o variables de entorno."""
        data: dict[str, str] = {}
        if self.env_path.exists() and self.env_path.is_file():
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#") or "=" not in stripped:
                            continue
                        k, _, v = stripped.partition("=")
                        val = v.strip()
                        if (val.startswith('"') and val.endswith('"')) or (
                            val.startswith("'") and val.endswith("'")
                        ):
                            val = val[1:-1]
                        data[k.strip()] = val
            except Exception:
                pass

        backend = (
            os.getenv("PERSISTENCE_BACKEND")
            or os.getenv("DB_ENGINE")
            or data.get("PERSISTENCE_BACKEND")
            or data.get("DB_ENGINE")
            or "sqlite"
        )
        database_url = (
            os.getenv("DATABASE_URL")
            or data.get("DATABASE_URL")
            or ("sqlite:///asistpy.db" if backend == "sqlite" else "")
        )
        completed = data.get("SETUP_COMPLETED", "").lower() in ("true", "1", "yes")

        return DesktopConfig(
            backend=backend,
            database_url=database_url,
            first_run_completed=completed,
            theme=data.get("GUI_THEME", "dark"),
        )

    def save(
        self,
        backend: str,
        database_url: str,
        first_run_completed: bool = True,
        theme: str = "dark",
        extra_vars: dict[str, str] | None = None,
    ) -> None:
        """Guarda la configuración seleccionada en el archivo .env y actualiza os.environ."""
        lines = [
            "# Configuración generada por AsistPy Desktop GUI",
            f"PERSISTENCE_BACKEND={backend}",
            f"DB_ENGINE={backend}",
            f"DATABASE_URL={database_url}",
            f"SETUP_COMPLETED={'true' if first_run_completed else 'false'}",
            f"GUI_THEME={theme}",
        ]

        if extra_vars:
            for k, v in extra_vars.items():
                lines.append(f"{k}={v}")

        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Actualizar entorno en tiempo de ejecución
        os.environ["PERSISTENCE_BACKEND"] = backend
        os.environ["DB_ENGINE"] = backend
        os.environ["DATABASE_URL"] = database_url
        os.environ["SETUP_COMPLETED"] = "true" if first_run_completed else "false"
        os.environ["GUI_THEME"] = theme

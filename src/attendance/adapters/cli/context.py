import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from attendance.adapters.persistence.factory import PersistenceBundle, PersistenceFactory


def get_common_parser() -> argparse.ArgumentParser:
    """Crea un parser auxiliar con opciones globales para heredar en subparsers."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--env-file",
        default=argparse.SUPPRESS,
        help="Ruta a un archivo .env personalizado con variables de entorno.",
    )
    parser.add_argument(
        "--backend",
        default=argparse.SUPPRESS,
        help="Sobrescribe el motor de persistencia (sqlite, postgres, mysql, sqlserver, memory).",
    )
    parser.add_argument(
        "--db-url",
        default=argparse.SUPPRESS,
        help="Sobrescribe la cadena de conexión a la base de datos (DATABASE_URL).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Habilita depuración detallada y trazas completas de error.",
    )
    return parser


def load_env_file(env_path: str | Path | None = None) -> None:
    """Carga variables desde un archivo .env si existe, sin sobreescribir variables ya definidas."""
    target_path = Path(env_path) if env_path else Path(".env")
    if not target_path.exists() or not target_path.is_file():
        return

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, _, val = stripped.partition("=")
                key = key.strip()
                val = val.strip()
                # Quitar comillas si las tiene
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                if key not in os.environ:
                    os.environ[key] = val
    except Exception:
        # Si no se puede leer el archivo .env, se continúa silenciosamente
        pass


@dataclass
class CLIContext:
    """Mantiene el estado global de configuración y acceso a repositorios para comandos CLI."""

    backend: str | None = None
    db_url: str | None = None
    verbose: bool = False
    stdout: TextIO | None = None

    def get_bundle(self, init_tables: bool = False) -> PersistenceBundle:
        """Obtiene el conjunto de repositorios configurado para la base de datos."""
        return PersistenceFactory.create_bundle(
            backend=self.backend,
            connection_string=self.db_url,
            init_tables=init_tables,
        )

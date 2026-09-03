"""Gestión de conexiones, Engine y sesiones de SQLAlchemy 2.0.

Agnóstico respecto al motor (SQLite, PostgreSQL, MySQL, SQL Server).
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from attendance.adapters.persistence.sql.models import Base


def create_db_engine(database_url: str, **kwargs: Any) -> Engine:
    """Crea una instancia de Engine de SQLAlchemy configurada según el dialecto."""
    engine_kwargs: dict[str, Any] = dict(kwargs)

    # Optimizaciones específicas para SQLite
    if database_url.startswith("sqlite"):
        connect_args = engine_kwargs.setdefault("connect_args", {})
        connect_args.setdefault("check_same_thread", False)

    return create_engine(database_url, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones con expire_on_commit desactivado para desacoplamiento."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Crea todas las tablas definidas en los modelos en la base de datos destino."""
    Base.metadata.create_all(bind=engine)


def drop_db(engine: Engine) -> None:
    """Elimina todas las tablas (útil para pruebas y entornos de desarrollo limpios)."""
    Base.metadata.drop_all(bind=engine)


class Database:
    """Administrador de persistencia que encapsula el Engine y la factoría de sesiones."""

    def __init__(self, database_url: str, **engine_kwargs: Any) -> None:
        self.url = database_url
        self.engine = create_db_engine(database_url, **engine_kwargs)
        self.session_factory = create_session_factory(self.engine)

    def init_tables(self) -> None:
        """Inicializa las tablas en la base de datos."""
        init_db(self.engine)

    def drop_tables(self) -> None:
        """Elimina las tablas en la base de datos."""
        drop_db(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provee un contexto transaccional seguro con rollback automático ante errores."""
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

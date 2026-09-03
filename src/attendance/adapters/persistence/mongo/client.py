"""Adaptador base y cliente para bases de datos NoSQL / Documentales (MongoDB)."""

from typing import Any


class MongoClientWrapper:
    """Cliente base de conexión para MongoDB con validación de dependencias opcionales."""

    def __init__(self, uri: str, database_name: str = "asistpy") -> None:
        self.uri = uri
        self.database_name = database_name
        self._client: Any = None
        self._db: Any = None
        self._connect()

    def _connect(self) -> None:
        try:
            import pymongo
        except ImportError as exc:
            raise RuntimeError(
                "Para utilizar persistencia no relacional con MongoDB, "
                "debes instalar la dependencia opcional: pip install 'asistpy[mongo]'"
            ) from exc

        self._client = pymongo.MongoClient(self.uri)
        self._db = self._client[self.database_name]

    @property
    def db(self) -> Any:
        return self._db

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

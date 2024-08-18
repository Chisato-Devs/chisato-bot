from __future__ import annotations

from datetime import timedelta, datetime

from asyncpg import Pool, connection
from asyncpg.protocol import protocol

import utils.basic as basic


class ChisatoPool(Pool):
    _instance: ChisatoPool | None = None

    @classmethod
    def _to_cache(cls, obj: ChisatoPool) -> None:
        cls._instance = obj

    @classmethod
    def from_cache(cls) -> ChisatoPool:
        return cls._instance

    @classmethod
    def _remove_from_cache(cls) -> None:
        cls._instance = None

    def __init__(self, *args, **kwargs) -> None:
        self.client = basic.ChisatoBot.from_cache()
        self._to_cache(self)
        self.reconnect_timeout = datetime.now() + timedelta(seconds=20)

        self.__dsn = kwargs.get("dsn")
        super().__init__(*args, **kwargs)

    @property
    def connected(self) -> bool:
        return self._initialized

    async def reconnect(self: ChisatoPool) -> ChisatoPool:
        """
        Attempts to re-establish a connection to the database if the current connection is lost.

        Args:
            self (ChisatoPool): The ChisatoPool instance.

        Returns:
            ChisatoPool: The ChisatoPool instance.
        """
        if self.from_cache().reconnect_timeout < datetime.now():
            self._remove_from_cache()
            return await self.connect(self.__dsn)
        return self.from_cache()

    @classmethod
    async def connect(cls, dsn: str, /) -> ChisatoPool:
        """
        Connects to the database using the given DSN.

        Args:
            dsn (str): The data source name to use for connecting to the database.

        Returns:
            ChisatoPool: The connected database pool.
        """
        pool = cls(
            dsn=dsn,
            min_size=10,
            max_size=10,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
            setup=None,
            init=None,
            loop=None,
            connection_class=connection.Connection,
            record_class=protocol.Record
        )
        await pool._async__init__()
        return pool

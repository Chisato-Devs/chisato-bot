import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import asyncpg
from asyncpg.exceptions import ConnectionDoesNotExistError
from disnake.ext.tasks import loop
from loguru import logger

from utils.basic.services.database.handlers.pool import ChisatoPool


class Database:
    def __init__(
            self, pool: ChisatoPool
    ) -> None:
        """
        This class is used to handle all database interactions.

        Args:
            pool (ChisatoPool): The database connection pool.
        """
        self._pool = pool
        self._lost_queries: dict[str, Any] = {}

        if hasattr(self, "cluster") and (cluster := getattr(self, "cluster")):
            asyncio.create_task(self._setup(cluster))

        self.lost_queries_task.start()

    def _pops_from_lost_queries(self, keys: list[str]) -> None:
        """
        Removes the queries from the lost queries list that are in the keys list.

        Parameters:
            keys (list[str]): The keys of the queries to remove from the lost queries list.

        Returns:
            None
        """
        for i in keys:
            try:
                self._lost_queries.pop(i)
            except KeyError:
                pass

    @loop(seconds=10)
    async def lost_queries_task(self) -> None:
        """
        A task that periodically attempts to re-run any queries that were previously executed but failed due to a lost connection.

        This task runs every 10 seconds and attempts to re-run any queries that were previously added to the `_lost_queries` dictionary. If the connection to the database is still active, the query is executed using the `execute` method. If the execution fails, the exception is logged using `loguru`. If the execution is successful, the query is removed from the `_lost_queries` dictionary.

        Parameters:
            self (Database): The instance of the `Database` class that contains the `_lost_queries` dictionary and the `this_pool` property.

        Returns:
            None
        """
        if self._lost_queries and self._pool.connected:
            handled = []
            for sql, args in self._lost_queries.items():
                try:
                    await self.execute(sql, *args)
                except Exception as e:
                    logger.warning(e)
                else:
                    handled.append(sql)
            self._pops_from_lost_queries(handled)

    @staticmethod
    async def _get_script(folder: str, name: str) -> str:
        """
        This function is used to read a SQL script from the specified folder and return it as a string.

        Parameters:
            folder (str): The name of the folder containing the SQL script.
            name (str): The name of the SQL script file.

        Returns:
            str: The contents of the SQL script.
        """
        async with aiofiles.open(
                Path(f'./utils/basic/services/database/scripts/{folder}/{name}.sql'),
                encoding='utf-8'
        ) as f:
            return await f.read()

    @property
    def this_pool(self) -> ChisatoPool:
        return self._pool

    async def reconnect(self) -> None:
        self._pool = await self._pool.reconnect()

    async def _setup(self, cluster: str) -> None:
        script = await self._get_script(folder='create_tables', name=cluster)
        if script:
            await self.execute(script)

    async def close(self) -> None:
        await self._pool.close()
        logger.info(f"Connection {self.cluster} was closed successfully")  # type: ignore

    async def execute(self, sql: str, *args: Any) -> None:
        """
        Executes the provided SQL statement, with the provided arguments, on the database.

        Parameters:
            sql (str): The SQL statement to execute.
            *args (Any): The arguments to pass to the SQL statement.

        Returns:
            None

        Raises:
            asyncpg.Error: If the query fails.
        """
        if not self._pool.connected:
            self._lost_queries[sql] = args
            return None

        try:
            await self._pool.execute(sql, *args)
        except OSError:
            self._lost_queries[sql] = args
        except ConnectionDoesNotExistError as e:
            self._lost_queries[sql] = args
            logger.error(e)

        return None

    async def executemany(self, sql: str, *args: Any) -> None:
        """
        Executes the provided SQL statement, with the provided arguments, on the database.

        Parameters:
            sql (str): The SQL statement to execute.
            *args (Any): The arguments to pass to the SQL statement.

        Returns:
            None

        Raises:
            asyncpg.Error: If the query fails.
        """
        if not self._pool.connected:
            self._lost_queries[sql] = args
            return None

        try:
            await self._pool.executemany(sql, *args)
        except OSError:
            self._lost_queries[sql] = args
        except ConnectionDoesNotExistError as e:
            self._lost_queries[sql] = args
            logger.error(e)

        return None

    async def fetchall(self, sql: str, *args: Any) -> list[asyncpg.Record]:
        """
        Executes the provided SQL statement, with the provided arguments, on the database.

        Parameters:
            sql (str): The SQL statement to execute.
            *args (Any): The arguments to pass to the SQL statement.

        Returns:
            list[asyncpg.Record] | None: A list of records returned by the query,
            or None if the connection to the database is lost.

        Raises:
            asyncpg.Error: If the query fails.
        """
        if not self._pool.connected:
            return []

        try:
            return await self._pool.fetch(sql, *args)
        except (ConnectionDoesNotExistError, OSError) as e:
            logger.error(e)

        return []

    async def fetchrow(self, sql: str, *args: Any) -> asyncpg.Record | None:
        """
        Executes the provided SQL statement, with the provided arguments, on the database.

        Parameters:
            sql (str): The SQL statement to execute.
            *args (Any): The arguments to pass to the SQL statement.

        Returns:
            asyncpg.Record | None: A record returned by the query, or None if the connection to the database is lost.

        Raises:
            asyncpg.Error: If the query fails.
        """
        if not self._pool.connected:
            return None

        try:
            return await self._pool.fetchrow(sql, *args)
        except (ConnectionDoesNotExistError, OSError) as e:
            logger.error(e)

    async def fetchval(self, sql: str, *args: Any) -> Any:
        """
        Executes the provided SQL statement, with the provided arguments, on the database.

        Args:
            sql (str): The SQL statement to execute.
            *args (Any): The arguments to pass to the SQL statement.

        Returns:
            Any: The value returned by the query.

        Raises:
            asyncpg.Error: If the query fails.
        """
        if not self._pool.connected:
            return None

        try:
            return await self._pool.fetchval(sql, *args)
        except (ConnectionDoesNotExistError, OSError) as e:
            logger.error(e)

from __future__ import annotations

from datetime import datetime

from asyncpg import Record

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.enviroment import env


class AdminDB(Database):
    __slots__ = (
        'bot'
    )

    cluster: str = "admin"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)
        self.bot = self.this_pool.client

    async def get_data_uses(self, name: str, per_day: bool = False) -> Record | None:
        """
        Hru-hru-hru
        :return: int object
        """
        if per_day:
            data = await self.fetchval('select uses from analytics_commands_per_day where command = $1', name)
        else:
            data = await self.fetchval('select uses from analytics_commands_all_time where command = $1', name)

        return data

    async def reg_command(self, name: str) -> None:
        """
        Register command in table
        :param name: string
        :return: None
        """
        if not await self.get_data_uses(name=name):
            await self.execute('insert into analytics_commands_all_time(command) values ($1)', name)
        else:
            await self.execute('update analytics_commands_all_time set uses=uses + 1 where command = $1', name)

        if not await self.get_data_uses(name=name, per_day=True):
            await self.execute('insert into analytics_commands_per_day(command) values ($1)', name)
        else:
            await self.execute('update analytics_commands_per_day set uses=uses + 1 where command = $1', name)

    async def get_analytics_commands_data(self, per_day: bool = False) -> list[Record] | None:
        """
        Get the data from local admin database
        :param per_day: boolean
        :return: list with tuples or None
        """

        if per_day:
            return await self.fetchall('select * from analytics_commands_per_day')
        else:
            return await self.fetchall('select * from analytics_commands_all_time')

    async def get_analytics_logs_data(self) -> list[Record] | None:
        """
        Get the data from local admin database
        :return: list with tuples or None
        """
        return await self.fetchall('select * from analytics_logs')

    async def truncate_analytics_per_day(self) -> None:
        """
        Truncate the analytics data per day from database
        :return: None
        """
        await self.execute('truncate table analytics_commands_per_day')
        await self.execute("truncate table analytics_logs")

    async def reg_to_analytics(self, type: str, **kwargs) -> None:
        """
        Add a new analytic row to table
        :param type: str
        :return: None
        """

        if self.bot and self.bot.user.id == env.MAIN_ID:
            await self.execute(
                'insert into analytics_logs(type, date, args) VALUES ($1, $2, $3)',
                type, str(datetime.now().timestamp()), str(kwargs)
            )

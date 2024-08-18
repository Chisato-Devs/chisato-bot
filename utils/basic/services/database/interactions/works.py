import json
from typing import Optional

import aiofiles

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.dataclasses import Work
from utils.exceptions.errors import (
    AlreadyHaveWork,
    DoesntHaveWork
)


class WorksDB(Database):
    __slots__ = (
        "bot"
    )

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)
        self.bot = self.this_pool.client
        self.bot.loop.create_task(self._load_works())

        self._works: dict[str, Work] = {}

    async def _load_works(self) -> None:
        async with aiofiles.open(f"./json/works.json", encoding="utf-8") as f:
            json_data = json.loads(await f.read())

        for work_dict in json_data:
            self._works[work_dict["name"]] = Work(
                name=work_dict["name"],
                initial_payment=work_dict["initial_payment"],
                final_payment=work_dict["final_payment"],
                initial_premium=work_dict["initial_premium"],
                final_premium=work_dict["final_premium"],
                need_works_count=work_dict["need_works_count"]
            )

    def get_work(self, name: str) -> Work:
        return self._works.copy()[name]

    async def add(self, member: int, guild: int, work_type: str) -> None:
        await self.bot.databases.economy.member_check_in_main_db(guild=guild, members=[member])

        if await self.fetchval(
                "SELECT work FROM economy_main WHERE guild_id=$1 AND user_id=$2",
                guild, member
        ):
            raise AlreadyHaveWork

        await self.execute(
            "UPDATE economy_main SET work=$1 WHERE guild_id=$2 AND user_id=$3", work_type, guild, member
        )

    async def remove(self, member: int, guild: int) -> None:
        await self.bot.databases.economy.member_check_in_main_db(guild=guild, members=[member])

        if not (
                await self.fetchrow(
                    "SELECT work FROM economy_main WHERE guild_id=$1 AND user_id=$2", guild, member
                )
        ):
            raise DoesntHaveWork

        await self.execute(
            "UPDATE economy_main SET work=NULL WHERE guild_id=$1 AND user_id=$2",
            guild, member
        )

    async def count_update(self, member: int, guild: int) -> None:
        await self.bot.databases.economy.member_check_in_main_db(guild=guild, members=[member])

        if not (
                await self.fetchrow(
                    "SELECT work FROM economy_main WHERE guild_id=$1 AND user_id=$2", guild, member
                )
        ):
            raise DoesntHaveWork

        await self.execute(
            "UPDATE economy_main SET works_count=works_count+1 WHERE guild_id=$1 AND user_id=$2", guild, member
        )

    async def values(self, member: int, guild: int) -> tuple[Optional[int], Optional[int]]:
        await self.bot.databases.economy.member_check_in_main_db(guild=guild, members=[member])

        values = await self.fetchrow(
            "SELECT work, works_count FROM economy_main WHERE guild_id=$1 AND user_id=$2",
            guild, member
        )
        return (
            values[0], values[1]
        )

import asyncio
from collections import defaultdict
from random import randint
from typing import TYPE_CHECKING

import asyncpg
from asyncpg import Record
from disnake import TextChannel, VoiceChannel, ForumChannel, StageChannel, Member, Guild
from disnake.ext.tasks import loop

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.exceptions import MaxPrestige, NotIs100

if TYPE_CHECKING:
    pass


class LevelsDB(Database):
    __slots__ = (
        "bot",
        "_can_exp"
    )

    cluster: str = "levels"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)

        self.bot = self.this_pool.client
        self._member_lock = asyncio.Lock()
        self._settings_lock = asyncio.Lock()
        self._can_exp: dict[Guild, dict[Member, bool]] = defaultdict(defaultdict)
        self._clear_can_exp.start()

    @loop(minutes=1)
    async def _clear_can_exp(self) -> None:
        self._can_exp.clear()

    @staticmethod
    def calculate_experience(level: int) -> int:
        min_experience = 30
        max_experience = 1000

        experience = min_experience + (max_experience - min_experience) * level / 100
        return round(experience)

    async def settings_values(self, guild: int) -> None | asyncpg.Record:
        await self._settings_if_not_exists(guild)
        return await self.fetchrow('SELECT * FROM levels_settings WHERE guild_id=$1', guild)

    async def get_member_values(self, guild: int, member: int) -> None | asyncpg.Record:
        return await self.fetchrow(
            'SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild, member
        )

    async def _settings_if_not_exists(self, guild: int) -> None:
        async with self._settings_lock:
            await self.execute(
                """
                INSERT INTO levels_settings (guild_id)
                SELECT $1
                WHERE NOT EXISTS (SELECT 1 FROM levels_settings WHERE guild_id = $1)
                """,
                guild
            )

    async def settings_status_switch(self, guild: int, alert: bool = False) -> bool:
        await self._settings_if_not_exists(guild)
        if not alert:
            if (await self.settings_values(guild))[2]:
                await self.execute("UPDATE levels_settings SET status=FALSE WHERE guild_id=$1", guild)
                return False
            else:
                await self.execute("UPDATE levels_settings SET status=TRUE WHERE guild_id=$1", guild)
                return True
        else:
            if (await self.settings_values(guild))[1]:
                await self.execute("UPDATE levels_settings SET alert=FALSE WHERE guild_id=$1", guild)
                return False
            else:
                await self.execute("UPDATE levels_settings SET alert=TRUE WHERE guild_id=$1", guild)
                return True

    async def set_embed_data(self, guild: int, embed_data: str = None) -> None:
        await self._settings_if_not_exists(guild)

        if embed_data:
            await self.execute("UPDATE levels_settings SET embed_data=$1 WHERE guild_id=$2", embed_data, guild)
        else:
            await self.execute("UPDATE levels_settings SET embed_data=NULL WHERE guild_id=$1", guild)

    async def add_member_to_table(self, guild: int, member: int) -> None:
        async with self._member_lock:
            await self.execute(
                """
                INSERT INTO levels_main (guild_id, user_id)
                SELECT $1, $2
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM levels_main 
                    WHERE guild_id = $1 AND user_id = $2
                )
                """,
                guild, member
            )

    async def select_data(self, guild: int, member: int) -> Record:
        await self.add_member_to_table(guild=guild, member=member)
        return await self.fetchrow('SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild, member)

    async def passive_exp(
            self, guild: Guild, member: Member,
            channel: TextChannel | VoiceChannel | ForumChannel | StageChannel,
            *, bot: 'ChisatoBot'
    ) -> None:
        if not ((s := await self.bot.databases.level.settings_values(guild=guild.id)) and s[2]):
            return

        await self.add_member_to_table(guild=guild.id, member=member.id)
        if not (self._can_exp.get(guild, {}).get(member, True)):
            return

        self._can_exp[guild][member] = False
        values = await self.fetchrow(
            'SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild.id, member.id
        )
        if values[5] < values[4]:
            if values[4] == 1000 and values[5] >= 970:
                await self.execute(
                    "UPDATE levels_main SET exp_now=1000 WHERE guild_id=$1 AND user_id=$2",
                    guild.id, member.id
                )
            else:
                await self.execute(
                    "UPDATE levels_main SET exp_now=exp_now+$3 WHERE guild_id=$1 AND user_id=$2",
                    guild.id, member.id, randint(1, 20)
                )

        values = await self.fetchrow(
            'SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild.id, member.id
        )
        if values[4] <= values[5]:
            if values[2] == 10 and values[3] == 100:
                return

            await self.execute(
                "UPDATE levels_main SET level=level+1, exp_now=0, exp_need=$1 WHERE guild_id=$2 AND user_id=$3",
                self.calculate_experience(values[3] + 1), guild.id, member.id
            )
            bot.dispatch(
                'member_level_upped',
                guild, member, channel
            )

    async def check_now_prestige(self, guild: int, member: int) -> bool:
        await self.add_member_to_table(guild=guild, member=member)

        values = await self.fetchrow('SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild, member)
        if values[3] == 100 and values[2] < 10:
            return True

        return False

    async def set_prestige(self, id: int, guild: int, member: int) -> None:
        await self.execute(
            'UPDATE levels_main SET prestige=$1 WHERE guild_id=$2 AND user_id=$3', id, guild, member
        )

    async def set_level(self, id: int, guild: int, member: int) -> None:
        await self.execute(
            'UPDATE levels_main SET level=$1, exp_now=0, exp_need=$2 WHERE guild_id=$3 AND user_id=$4',
            id, self.calculate_experience(id), guild, member
        )

    async def prestige(self, guild: int, member: int) -> None:
        await self.add_member_to_table(guild=guild, member=member)

        values = await self.fetchrow('SELECT * FROM levels_main WHERE guild_id=$1 AND user_id=$2', guild, member)
        if values[2] == 10:
            raise MaxPrestige

        if values[3] == 100:
            await self.execute(
                "UPDATE levels_main SET prestige=prestige+1, exp_need=30, exp_now=0, level=0 "
                "WHERE guild_id=$1 AND user_id=$2",
                guild, member
            )

            if role_id := await self.fetchrow(
                    'SELECT role_id FROM levels_prestige_rewards WHERE guild_id=$1 AND prestige_id=$2',
                    guild, values[2] + 1
            ):
                return role_id

        else:
            raise NotIs100

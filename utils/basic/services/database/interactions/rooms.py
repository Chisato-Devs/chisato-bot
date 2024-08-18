from datetime import timedelta

from asyncpg import Record
from disnake import Member, MessageInteraction
from disnake.utils import utcnow

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database


class RoomsDB(Database):
    __slots__ = (
        "bot"
    )

    cluster: str = "rooms"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)

        self.bot = self.this_pool.client

    async def create_room(self, guild: int, voice: int, user: Member) -> None:
        await self.execute(
            'INSERT INTO rooms_temp_data(guild_id, voice_id, leader) VALUES($1, $2, $3)',
            guild, voice, user.id
        )

    async def create_love_room(self, guild: int, voice: int, user: Member) -> None:
        await self.execute(
            'INSERT INTO rooms_temp_data(guild_id, voice_id, leader, is_love) VALUES($1, $2, $3, True)',
            guild, voice, user.id
        )

    async def temp_room_values(self, guild: int, user: int) -> Record | None:
        return await self.fetchrow(
            'SELECT * FROM rooms_temp_data WHERE guild_id=$1 AND leader=$2',
            guild, user
        )

    async def is_love_room(self, interaction: MessageInteraction) -> bool:
        return await self.fetchval(
            "SELECT is_love FROM rooms_temp_data WHERE guild_id=$1 AND voice_id=$2",
            interaction.guild.id, interaction.author.voice.channel.id
        )

    async def temp_room_values_with_channel(self, guild: int, channel: int) -> Record | None:
        return await self.fetchrow(
            'SELECT * FROM rooms_temp_data WHERE guild_id=$1 AND voice_id=$2', guild, channel
        )

    async def settings_room_insert(self, guild: int, user: Member, room_naming: int = None,
                                   limit_user: int = None) -> None:
        result = await self.fetchrow(
            'SELECT * FROM rooms_users_setting WHERE guild_id=$1 AND user_id=$2', guild, user.id
        )

        if room_naming:
            if result:
                await self.execute(
                    'UPDATE rooms_users_setting SET room_name=$1 WHERE guild_id=$2 AND user_id=$3',
                    room_naming, guild, user.id
                )
            else:
                await self.execute(
                    'INSERT INTO rooms_users_setting(guild_id, user_id, room_name) VALUES($1, $2, $3)',
                    guild, user.id, room_naming
                )

        elif room_naming == 0:
            if result:
                await self.execute(
                    'UPDATE rooms_users_setting SET room_name=NULL WHERE guild_id=$1 AND user_id=$2',
                    guild, user.id
                )
            else:
                await self.execute(
                    'INSERT INTO rooms_users_setting(guild_id, user_id) VALUES($1, $2)',
                    guild, user.id
                )

        if limit_user:
            if result:
                await self.execute(
                    'UPDATE rooms_users_setting SET limit_users=$1 WHERE guild_id=$2 AND user_id=$3',
                    limit_user, guild, user.id
                )
            else:
                await self.execute(
                    'INSERT INTO rooms_users_setting(guild_id, user_id, limit_users) VALUES($1, $2, $3)',
                    guild, user.id, limit_user
                )

        elif limit_user == 0:
            if result:
                await self.execute(
                    'UPDATE rooms_users_setting SET limit_users=NULL WHERE guild_id=$1 AND user_id=$2', guild, user.id
                )
            else:
                await self.execute(
                    'INSERT INTO rooms_users_setting(guild_id, user_id) VALUES($1, $2)',
                    guild, user.id
                )

    async def settings_values(self, guild: int, user: int) -> Record | None:
        return await self.fetchrow(
            'SELECT * FROM rooms_users_setting WHERE guild_id=$1 AND user_id=$2',
            guild, user
        )

    async def remove_room(self, guild: int, voice: int) -> None:
        await self.execute(
            'DELETE FROM rooms_temp_data WHERE guild_id=$1 AND voice_id=$2',
            guild, voice
        )

    async def get_all_settings(self) -> list[Record]:
        return await self.fetchall(
            "SELECT * FROM rooms_guild_settings"
        )

    async def room_check_find(self, guild: int) -> Record | None:
        return await self.fetchrow('SELECT * FROM rooms_guild_settings WHERE guild_id=$1', guild)

    async def room_setup_remove(self, guild: int) -> None:
        await self.execute(
            'DELETE FROM rooms_guild_settings WHERE guild_id=$1', guild
        )

    async def room_settings_remove(self, guild: int) -> None:
        await self.execute('DELETE FROM rooms_users_setting WHERE guild_id=$1', guild)

    async def rooms_voice_channels_fetch(self, guild: int) -> list[Record]:
        return await self.fetchall(
            'SELECT * FROM rooms_temp_data WHERE guild_id=$1', guild
        )

    async def rooms_remove_rooms(self, guild: int) -> None:
        await self.execute('DELETE FROM rooms_temp_data WHERE guild_id=$1', guild)

    async def room_req_add(self, guild: int, voice: int) -> None:
        time = utcnow() + timedelta(minutes=7)
        await self.execute(
            'UPDATE rooms_temp_data SET requests=$1, requests_time=$2 WHERE guild_id=$3 AND voice_id=$4',
            1, time.timestamp(), guild, voice
        )

    async def room_req_check(self, guild: int, voice: int) -> Record | None:
        result = await self.fetchrow(
            'SELECT requests FROM rooms_temp_data WHERE guild_id=$1 AND voice_id=$2', guild, voice
        )

        return result if result[0] == 1 else None

    async def room_req_checker(self, current_time: int) -> list[Record] | None:
        if not (data := await self.fetchall(
                'SELECT * FROM rooms_temp_data WHERE requests_time <= $1', current_time
        )):
            return []
        return data

    async def room_req_remove(self, guild: int, voice: int) -> None:
        await self.execute(
            'UPDATE rooms_temp_data SET requests=$1, requests_time=NULL WHERE guild_id=$2 AND voice_id=$3',
            0, guild, voice
        )

    async def room_update_leader(self, guild: int, voice: int, new_leader: int) -> None:
        await self.execute(
            "UPDATE rooms_temp_data SET leader=$1 WHERE guild_id=$2 AND voice_id=$3",
            new_leader, guild, voice
        )

    async def room_setup_insert(
            self, guild: int, voice_channel: int, msg_id: int, category: int, text_channel: int,
            love_channel: int | None
    ) -> None:
        await self.execute(
            """
            INSERT INTO rooms_guild_settings(guild_id, category, founder, message_id, channel, love_room) 
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            guild, category, voice_channel, msg_id, text_channel, love_channel
        )

    async def room_update_setup(
            self, guild: int, msg_id: int
    ) -> bool:
        if await self.fetchall('select message_id from rooms_guild_settings where guild_id=$1', guild):
            await self.execute('update rooms_guild_settings set message_id=$1 where guild_id=$2', msg_id, guild)
            return True
        return False

    async def room_update_love_room(
            self, guild: int, love_id: int = None
    ) -> bool:
        if await self.fetchall('select love_room from rooms_guild_settings where guild_id=$1', guild):
            await self.execute(
                'update rooms_guild_settings set love_room=$1 where guild_id=$2',
                love_id, guild
            )
            return True

        return False

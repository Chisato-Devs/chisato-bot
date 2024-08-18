import ast
import asyncio

from asyncpg import Record
from disnake import Guild

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database


class SettingsDB(Database):
    __slots__ = (
        "bot",
    )

    cluster: str = "settings"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)
        self.bot = self.this_pool.client
        self._lock = asyncio.Lock()

    async def _check_if_in_db(self, *, guild: int) -> None:
        """
        :param guild: integer
        :return: None, but insert new row in database with guild
        """
        async with self._lock:
            await self.execute(
                """
                INSERT INTO settings_main (guild_id)
                SELECT $1
                WHERE NOT EXISTS (SELECT 1 FROM settings_main WHERE guild_id = $1)
                """,
                guild
            )

    async def get(self, *, guild: int) -> Record | None:
        """
        :param guild: int
        :return: tuple obj with all information in table with this guild
        """
        await self._check_if_in_db(guild=guild)

        return await self.fetchrow('select * from settings_main where guild_id=$1', guild)

    async def get_lang(self, *, guild: int) -> str:
        """
        :param guild: int, guild_id
        :return: language
        """
        await self._check_if_in_db(guild=guild)

        if values := await self.fetchrow('select * from settings_main where guild_id=$1', guild):
            return values[3]
        else:
            return 'ru'

    async def insert(
            self, guild: int, *, language: str = None,
            banner: str = None
    ) -> bool:
        """
        :param guild: int, guild_id (disnake.Guild.id)
        :param language: str,
        :param banner: str, banner_name
        :return: bool
        """
        await self._check_if_in_db(guild=guild)

        if language:
            _language = await self.fetchval('select language from settings_main where guild_id=$1', guild)

            await self.execute('update settings_main set language=$1 where guild_id=$2', language, guild)
            return False if _language else True

        if banner:
            banner_name = await self.fetchrow('select banner from settings_main where guild_id=$1', guild)

            await self.execute('update settings_main set banner=$1 where guild_id=$2', banner, guild)
            return False if banner_name else True

    async def remove(
            self, guild: int, *,
            banner: bool = None, economy: bool = None
    ) -> bool:
        """
        :param guild: bool
        :param banner: bool
        :param economy: bool
        :return: bool
        """
        await self._check_if_in_db(guild=guild)

        if banner:
            if await self.fetchval('select banner from settings_main where guild_id=$1', guild):
                await self.execute('update settings_main set banner=NULL where guild_id=$1', guild)
                return True
            return False

        if economy:
            if await self.fetchval('select economy from settings_main where guild_id=$1', guild):
                await self.execute('update settings_main set economy=False where guild_id=$1', guild)
                return True
            return False

    async def switch(
            self, *, guild: int, economy: bool = None
    ) -> None:
        """
        :param guild: int, guild_id (disnake.Guild.id)
        :param economy: If true, switch economy status
        :return: None
        """
        data = await self.get(guild=guild)

        if economy:
            if data[2]:
                await self.execute('update settings_main set economy=false where guild_id=$1', guild)
            else:
                await self.execute('update settings_main set economy=True where guild_id=$1', guild)

    async def _check_in_settings_logs(self, guild: Guild) -> None:
        if not await self.fetchval('select guild_id from settings_logs where guild_id=$1', guild.id):
            await self.execute('insert into settings_logs(guild_id) values ($1)', guild.id)

    async def get_logs_settings(self, guild: Guild) -> Record:
        await self._check_in_settings_logs(guild=guild)
        return await self.fetchrow("select * from settings_logs where guild_id=$1", guild.id)

    async def switch_logs(
            self,
            guild: Guild,
            server_status: int | bool = None,
            channels_status: int | bool = None,
            members_status: int | bool = None,
            messages_status: int | bool = None,
            automod_status: int | bool = None
    ) -> None:
        await self._check_in_settings_logs(guild=guild)

        if server_status is not None:
            if not server_status:
                await self.execute('update settings_logs set server_status=NULL where guild_id=$1', guild.id)
            else:
                await self.execute(
                    'update settings_logs set server_status=$1 where guild_id=$2',
                    server_status, guild.id
                )

        if channels_status is not None:
            if not channels_status:
                await self.execute('update settings_logs set channels_status=NULL where guild_id=$1', guild.id)
            else:
                await self.execute(
                    'update settings_logs set channels_status=$1 where guild_id=$2', channels_status, guild.id
                )

        if members_status is not None:
            if not members_status:
                await self.execute('update settings_logs set members_status=NULL where guild_id=$1', guild.id)
            else:
                await self.execute(
                    'update settings_logs set members_status=$1 where guild_id=$2',
                    members_status, guild.id
                )

        if messages_status is not None:
            if not messages_status:
                await self.execute('update settings_logs set messages_status=NULL where guild_id=$1', guild.id)
            else:
                await self.execute(
                    'update settings_logs set messages_status=$1 where guild_id=$2', messages_status, guild.id
                )

        if automod_status is not None:
            if not automod_status:
                await self.execute('update settings_logs set automod_status=NULL where guild_id=$1', guild.id)
            else:
                await self.execute(
                    'update settings_logs set automod_status=$1 where guild_id=$2', messages_status, guild.id
                )

    async def set_permission_to_command(self, cmd_name: str, *, guild: int, roles: list[int]) -> None:
        if not await self.get_permissions(cmd_name=cmd_name, guild=guild):
            return await self.execute(
                'insert into settings_permissions_roles(guild_id, command_name, roles_ids) VALUES ($1, $2, $3)',
                guild, cmd_name, str(roles)
            )

        await self.execute(
            'update settings_permissions_roles set roles_ids=$1 where guild_id=$2 and command_name=$3',
            str(roles), guild, cmd_name
        )

    async def get_all_permissions(self, guild: int) -> list[Record]:
        return await self.fetchall(
            'select * from settings_permissions_roles where guild_id=$1', guild
        )

    async def get_permissions(self, cmd_name: str, *, guild: int) -> list[int]:
        c = await self.fetchval(
            'select roles_ids from settings_permissions_roles where command_name=$1 and guild_id=$2',
            cmd_name, guild
        )

        return ast.literal_eval(c) if c else []

    async def get_guilds_with_banners(self) -> list[Record]:
        return await self.fetchall(
            "SELECT guild_id, banner FROM settings_main WHERE banner IS NOT NULL"
        )

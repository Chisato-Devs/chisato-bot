from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from disnake import Guild
from loguru import logger

from utils.enviroment import env
from .handlers import Database, ChisatoPool
from .interactions.admin import AdminDB
from .interactions.cards import CardsDB
from .interactions.economy import EconomyDB
from .interactions.levels import LevelsDB
from .interactions.moderation import ModerationDB
from .interactions.music import MusicDB
from .interactions.pets import PetsDB
from .interactions.rooms import RoomsDB
from .interactions.settings import SettingsDB
from .interactions.transactions import TransactionsDB
from .interactions.works import WorksDB

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

__all__ = (
    "Databases"
)


class Databases:
    __slots__ = (
        "settings",
        "rooms",
        "level",
        "economy",
        "works",
        "transactions",
        "pets",
        "admin",
        "cards",
        "moderation",
        "music",
        "pool",
        "_last_check"
    )

    def __init__(self, pool: ChisatoPool) -> None:
        self.pool = pool

        self.settings = SettingsDB(pool=pool)

        self.rooms = RoomsDB(pool=pool)

        self.level = LevelsDB(pool=pool)

        self.economy = EconomyDB(pool=pool)
        self.works = WorksDB(pool=pool)
        self.transactions = TransactionsDB(pool=pool)
        self.pets = PetsDB(pool=pool)

        self.cards = CardsDB(pool=pool)

        self.admin = AdminDB(pool=pool)

        self.moderation = ModerationDB(pool=pool)

        self.music = MusicDB(pool=pool)

        self._last_check = 0

    @classmethod
    async def create(cls, bot: ChisatoBot) -> None:
        """
        Creates a new instance of the Databases class and sets it as the bot's database attribute.

        Parameters
        -----------
        bot: :class:`utils.basic.ChisatoBot`
            The bot instance that the database will be associated with.
        """
        bot.databases = cls(pool=await ChisatoPool.connect(env.DSN))

    def _send_error_log(self, e: Exception) -> None:
        logger.critical(f"{self.pool.__class__.__name__} raised error {e} ({type(e).__name__})")

    async def reload(self) -> None:
        """
        Reloads all the database connections.
        """
        for attr in dir(self):
            if attr.startswith('_') or callable(getattr(self, attr)):
                continue

            try:
                await getattr(self, attr).reconnect()
            except Exception as e:
                self._send_error_log(e)

    async def check(self) -> bool | Exception:
        """
        Checks the health of the database connection.

        Returns:
            bool: Whether the connection is healthy or not.
        """
        if self._last_check < datetime.now().timestamp():
            try:
                con = await self.pool.acquire()
                await self.pool.release(con)
            except Exception as e:
                self._send_error_log(e)
                return e

        if self._last_check < datetime.now().timestamp():
            self._last_check = (datetime.now() + timedelta(minutes=5)).timestamp()
        return False

    async def vipe_tables_from_guild(self, guild: Guild) -> None:
        async with self.pool.acquire() as c:
            for i in [
                "economy_main",
                "economy_bank",
                "economy_marry",
                "economy_pets",
                "economy_shop",
                "economy_transactions",
                "levels_main",
                "levels_prestige_rewards",
                "moderation_global_bans",
                "moderation_global_reports",
                "moderation_global_reports_settings",
                "moderation_global_warns",
                "moderation_global_warns_settings",
                "moderation_stats",
                "rooms_guild_settings",
                "rooms_temp_data",
                "rooms_users_setting",
                "settings_logs",
                "settings_main",
                "settings_permissions_roles"
            ]:
                await c.execute(f"DELETE FROM {i} WHERE guild_id = $1", guild.id)

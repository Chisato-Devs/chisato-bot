from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

from aiohttp import ClientSession
from disnake import (
    Intents,
    HTTPException,
    ApplicationCommandInteraction,
    InteractionResponded, NotFound
)
from disnake.ext.commands import (
    NoEntryPointError,
    ExtensionAlreadyLoaded,
    ExtensionNotFound,
    Context,
    CommandError,
    CommandOnCooldown,
    MissingAnyRole,
    MissingPermissions,
    NSFWChannelRequired,
    AutoShardedBot,
    NotOwner
)
from loguru import logger

from utils.basic.services.database import Databases
from utils.consts import ASCII_ART
from utils.enviroment import env
from utils.exceptions import DoesntHaveAgreedRole
from utils.exceptions.send_webhooks import WebhookSender


class ChisatoBot(AutoShardedBot):
    _instance: ChisatoBot | None = None

    @classmethod
    def _add_to_cache(cls, obj: ChisatoBot) -> ChisatoBot:
        cls._instance = obj
        return cls._instance

    @classmethod
    def from_cache(cls) -> ChisatoBot:
        return cls._instance

    def __init__(self, shard_count: int) -> None:
        self.databases: Databases | None = None
        self.webhooks = WebhookSender()

        self._session: Optional[ClientSession] = None

        logger.level("INFO", color="<fg #b6a0ff><bold>")

        self.disable_errors = False
        self._send_global_error = [
            CommandOnCooldown,
            MissingAnyRole,
            MissingPermissions,
            NSFWChannelRequired,
            DoesntHaveAgreedRole
        ]
        self._muted_errors = [
            NotFound
        ]

        intents = Intents.all()
        intents.presences = False

        super().__init__(
            command_prefix=env.PREFIX,
            help_command=None,
            intents=intents,
            shard_count=shard_count,
            owner_ids={484390171563917312, 975160842993692713}
        )
        self._add_to_cache(self)

        self._set_logger_schema()
        logger.info(ASCII_ART)

    @property
    def session(self) -> ClientSession:
        if not self._session:
            self._session = ClientSession()
        return self._session

    @staticmethod
    def _set_logger_schema() -> None:
        split = " <fg #b1b2ff>|</fg #b1b2ff> "

        logger.remove()
        logger.add(
            sys.stdout, colorize=True,
            format=(
                    "<level>{level: <6}</level>" + split +
                    "<fg #ff91ba>{name}:{function}:{line}</fg #ff91ba>" + split +
                    "<fg #ff5897>{time:YYYY-MM-DD HH:mm:ss}</fg #ff5897>" + split +
                    "<level>{message}</level>"
            )
        )

    def load_extension(self, name: str, *, package: Optional[str] = None) -> str:
        parts = name.split('.')
        try:
            super().load_extension(name, package=package)
        except NoEntryPointError:
            logger.warning(f"{parts[2]} doesn\'t have setup function!")
        except ExtensionAlreadyLoaded:
            logger.warning(f"{parts[2]} already loaded!")
        except ExtensionNotFound:
            logger.warning(f"{parts[2]} could not be loaded!")

        return list(reversed(parts))[0]

    def load_cogs(self):
        _load_cogs_cache = []
        for folder in os.listdir("./cogs"):
            if os.path.isdir(f"./cogs/{folder}"):
                for file in os.listdir(f"./cogs/{folder}"):
                    if file.endswith(".py"):
                        _load_cogs_cache.append(self.load_extension(f"cogs.{folder}.{file[:-3]}"))

                logger.info(f"Module {folder} ready! ({', '.join(_load_cogs_cache)})")
                _load_cogs_cache.clear()

    async def _didnt_respond_interaction(
            self, interaction: ApplicationCommandInteraction, exception: Exception
    ) -> None:
        await asyncio.sleep(1.5)
        if not hasattr(interaction, 'responded'):
            self.dispatch("didnt_respond_interaction", interaction, exception)

    async def on_slash_command_error(
            self, interaction: ApplicationCommandInteraction, exception: Exception
    ) -> None:
        if self.disable_errors:
            if type(exception) in self._muted_errors:
                return

            raise exception from exception

        if type(exception) in self._send_global_error:
            return self.dispatch(
                "global_slash_error", interaction, exception
            )

        try:
            await interaction.response.defer(ephemeral=True)
        except (
                HTTPException,
                TypeError,
                InteractionResponded
        ):
            return

        self.dispatch(
            f"{interaction.application_command.cog.__module__.split('.')[1].lower()}_error",
            interaction, exception
        )

        await self._didnt_respond_interaction(interaction, exception)

    async def on_command_error(self, context: Context, exception: CommandError) -> None:
        if isinstance(exception, NotOwner):
            return

        try:
            logger.warning(
                f"Context command ({context.command.qualified_name}) raised: \n"
                f"\"{type(exception).__name__}: {str(exception)}\""
            )
        except AttributeError:
            pass

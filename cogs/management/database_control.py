from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from disnake import Interaction, ui, HTTPException, Event, InteractionTimedOut
from disnake.ext.commands import Context, is_owner
from disnake.ext.tasks import loop
from loguru import logger

from utils.basic import CogUI, EmbedErrorUI, EmbedUI
from utils.basic.services.database import Databases
from utils.consts import ERROR_EMOJI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class DatabaseController(CogUI):
    __slots__ = (
        "bot", "tasks", "first_connect"
    )

    def __init__(self, bot: 'ChisatoBot') -> None:
        self.tasks = []
        self.first_connect = True
        super().__init__(bot)

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        self.check_database.start()

    def cog_unload(self) -> None:
        self.check_database.cancel()

    @CogUI.context_command(name='reload_database', aliases=['rd'])
    @is_owner()
    async def reload_database(self, ctx: Context) -> None:
        await ctx.message.delete()
        try:
            await self.reload()
        except Exception as e:
            await ctx.send(content=f"```{e.__class__.__name__}: {e}```")
            return

        await ctx.send("Успешно")

    async def _check(self) -> bool:
        try:
            con = await self.bot.databases.pool.acquire()
            await self.bot.databases.pool.release(con)

            return False
        except Exception as e:
            if not self.first_connect:
                logger.critical(
                    f"DATABASE RAISED AN EXCEPTION ON RELEASE {e.__class__.__name__}: {e}"
                )

            return True

    async def reload(self) -> None:
        try:
            if self.first_connect:
                await Databases.create(self.bot)
            else:
                await self.bot.databases.reload()
        except Exception as e:
            logger.critical(
                f"DATABASE RAISED AN EXCEPTION ON CREATING {e.__class__.__name__}: {e}"
            )
            await self.bot.loop.create_task(self.send_owners_message(e))
        else:
            if self.first_connect:
                logger.info("SUCCESS LOADED DATABASE")
            else:
                logger.info("SUCCESS RELOADED DATABASE")
        finally:
            self.first_connect = False

    @loop(minutes=30)
    async def check_database(self):
        if await self._check():
            await self.reload()

    @CogUI.listener(Event.interaction)
    async def catch_from_slash(self, interaction: Interaction) -> None:
        await self.for_pools(interaction)

    @staticmethod
    async def send_error_message(interaction: Interaction) -> None:
        data = {
            "embed": EmbedErrorUI(
                description=_t.get(
                    "database.description", locale=interaction.guild_locale
                ),
                member=interaction.author
            ),
            "components": [
                ui.Button(
                    label=_t.get(
                        "database.button.label",
                        locale=interaction.guild_locale
                    ),
                    url=env.GUILD_INVITE
                )
            ],
            "ephemeral": True
        }

        try:
            await interaction.send(**data)
        except InteractionTimedOut:
            pass
        except HTTPException:
            pass
        finally:
            del interaction

    async def send_owners_message(self, error: Exception) -> None:
        if self.bot.user and self.bot.user.id == env.MAIN_ID:
            await self.bot.webhooks.post(
                data={
                    "embeds": [
                        EmbedUI(
                            title=f"{ERROR_EMOJI} Ошибка базы данных",
                            description=f"> **Время:** {datetime.now()} | `{datetime.now().timestamp()}`\n"
                                        f"> **Причина:** {str(error)}\n"
                                        f"```py\n"
                                        f"{type(error).__name__}: {error}```"
                        )
                    ]
                },
                type='command'
            )

        logger.warning('Database is not defined')

    async def for_pools(self, interaction: Interaction) -> None:
        if self.bot.databases:
            if e := await self.bot.databases.check():
                await self.send_error_message(interaction)
                await self.send_owners_message(e)
                return

        elif not self.bot.databases:
            await self.send_error_message(interaction)
            await self.send_owners_message(Exception("Does't connected."))
            return


def setup(bot: ChisatoBot) -> None:
    bot.add_cog(DatabaseController(bot))

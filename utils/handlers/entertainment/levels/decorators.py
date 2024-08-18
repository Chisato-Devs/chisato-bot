from __future__ import annotations

from typing import Callable, TypeVar, TYPE_CHECKING

from disnake import ApplicationCommandInteraction
from disnake.ext.commands import check, Context

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/entertainment/levels.py")

__all__ = (
    "levels_on",
)


def levels_on() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
        bot: ChisatoBot = interaction.bot
        if (d := await bot.databases.level.settings_values(interaction.guild.id)) and d[2]:
            return True
        await interaction.response.send_message(
            embed=EmbedErrorUI(
                description=_t.get(
                    "level.error.disabled",
                    locale=interaction.guild_locale
                ),
                member=interaction.author
            ),
            ephemeral=True
        )
        return False

    return check(wrapper)

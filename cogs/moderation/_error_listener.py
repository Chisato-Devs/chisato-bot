from functools import cache
from typing import Callable, Optional, TYPE_CHECKING

from disnake import ApplicationCommandInteraction, Forbidden, HTTPException
from disnake.ext.commands import errors, MemberNotFound

from utils.basic import EmbedErrorUI, CogUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class ModerationErrorsListenerCog(CogUI):
    def __init__(self, bot: 'ChisatoBot') -> None:
        self.error_handling: dict[errors, Callable] = {
            MemberNotFound: self.member_not_found,
            Forbidden: self.forbidden,
            HTTPException: self.http_exception
        }

        super().__init__(bot)

    @CogUI.listener("on_moderation_error")
    async def catch_moderation_errors(
            self, interaction: ApplicationCommandInteraction, error: Exception
    ) -> None:
        error = getattr(error, 'original', error)
        if handler := self.get_handler(type(error)):
            interaction.responded = True
            await handler(interaction=interaction)

    @cache
    def get_handler(self, error_type: errors) -> Optional[Callable]:
        return self.error_handling.get(error_type)

    @staticmethod
    async def member_not_found(interaction: ApplicationCommandInteraction) -> None:
        embed = EmbedErrorUI(
            _t.get("mod.error_handler.member_not_found", locale=interaction.guild_locale), interaction.author
        )
        await interaction.followup.send(embed=embed)

    @staticmethod
    async def forbidden(interaction: ApplicationCommandInteraction) -> None:
        embed = EmbedErrorUI(
            _t.get("mod.error_handler.bot_forbidden", locale=interaction.guild_locale),
            interaction.author
        )
        await interaction.followup.send(embed=embed)

    @staticmethod
    async def http_exception(interaction: ApplicationCommandInteraction) -> None:
        embed = EmbedErrorUI(
            _t.get("mod.error_handler.http_exception", locale=interaction.guild_locale),
            interaction.author
        )
        await interaction.followup.send(embed=embed)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(ModerationErrorsListenerCog(bot))

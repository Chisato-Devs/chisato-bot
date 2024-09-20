from functools import cache
from typing import Callable, Optional, TYPE_CHECKING, Union

from disnake import ApplicationCommandInteraction
from disnake.ext.commands import errors, MemberNotFound

from utils import exceptions as custom_errors
from utils.basic import EmbedErrorUI, CogUI
from utils.exceptions import DecodeJsonError
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class FunErrorsListenerCog(CogUI):
    def __init__(self, bot: 'ChisatoBot') -> None:
        self.error_handling: dict[Union[errors, custom_errors], Callable] = {
            MemberNotFound: self.member_not_found,
            DecodeJsonError: self.json_error,
            # InvalidNodeException: self.node_exception
        }

        super().__init__(bot)

    @CogUI.listener("on_entertainment_error")
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
        embed = EmbedErrorUI(_t.get("fun.errors.member_not_found", locale=interaction.locale), interaction.author)
        await interaction.followup.send(embed=embed)

    @staticmethod
    async def node_exception(interaction: ApplicationCommandInteraction) -> None:
        embed = EmbedErrorUI(_t.get("fun.errors.node_exception", locale=interaction.locale), interaction.author)
        await interaction.followup.send(embed=embed)

    @staticmethod
    async def json_error(interaction: ApplicationCommandInteraction) -> None:
        embed = EmbedErrorUI(
            _t.get("fun.errors.404", locale=interaction.locale), interaction.author
        )
        await interaction.followup.send(embed=embed)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(FunErrorsListenerCog(bot))

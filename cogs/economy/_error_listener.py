from functools import cache
from typing import TYPE_CHECKING, Optional, Callable

from disnake import ApplicationCommandInteraction
from disnake.ext.commands import MemberNotFound

from utils.basic import CogUI, EmbedErrorUI
from utils.exceptions import errors, DoesntHavePet, DoesntHaveWork
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class EconomyErrorsListenerCog(CogUI):
    def __init__(self, bot: 'ChisatoBot') -> None:
        self.error_handling: dict[errors, Callable] = {
            DoesntHavePet: self._doesnt_have_pet,
            DoesntHaveWork: self._not_employed,
            MemberNotFound: self._not_found_member
        }

        super().__init__(bot)

    @cache
    def get_handler(self, error_type: errors) -> Optional[Callable]:
        return self.error_handling.get(error_type)

    @staticmethod
    async def _doesnt_have_pet(interaction: ApplicationCommandInteraction) -> None:
        await interaction.followup.send(
            embed=EmbedErrorUI(
                description=_t.get("eco.error.not_pet", locale=interaction.guild_locale),
                member=interaction.author
            )
        )

    @staticmethod
    async def _not_found_member(interaction: ApplicationCommandInteraction) -> None:
        await interaction.followup.send(
            embed=EmbedErrorUI(
                description=_t.get("eco.error.member_not_found", locale=interaction.guild_locale),
                member=interaction.author
            )
        )

    @staticmethod
    async def _not_employed(interaction: ApplicationCommandInteraction) -> None:
        await interaction.followup.send(
            embed=EmbedErrorUI(
                description=_t.get("eco.error.not_employed", locale=interaction.guild_locale),
                member=interaction.author
            )
        )

    @CogUI.listener("on_economy_error")
    async def catch_economy_errors(
            self, interaction: ApplicationCommandInteraction, error: Exception
    ) -> None:
        error = getattr(error, "original", error)
        if handler := self.get_handler(type(error)):
            interaction.responded = True
            await handler(interaction=interaction)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(EconomyErrorsListenerCog(bot))

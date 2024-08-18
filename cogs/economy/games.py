from typing import TYPE_CHECKING

from disnake import ApplicationCommandInteraction, Member, Localized
from disnake.ext.commands import Param

from utils.basic import CogUI
from utils.handlers.economy import decorators
from utils.handlers.economy.games import TicTacToeCommand
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class Games(CogUI):

    @CogUI.slash_command(name="game")
    @decorators.check_is_on()
    @decorators.check_in_fight()
    @decorators.check_in_game()
    async def _game(
            self, interaction: ApplicationCommandInteraction
    ) -> ...: ...

    @_game.sub_command(
        name="tic-tac-toe",
        description=Localized(
            "🎮 Игры: крестики-нолики! Сыграй с другом на ставку!",
            data=_t.get("games.tic_tac_toe.command.description")
        )
    )
    async def tictactoe(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("games.tic_tac_toe.command.option.member.name")),
                description=Localized(
                    "- выбери участника, с кем хочешь поиграть!",
                    data=_t.get("games.tic_tac_toe.command.option.member.description")
                ),
                default="ai"
            ),
            amount: int = Param(
                name=Localized("ставка", data=_t.get("games.tic_tac_toe.command.option.amount.name")),
                description=Localized(
                    "- укажи ставку для игры (Если не выбран участник, ставка не учитывается.)",
                    data=_t.get("games.tic_tac_toe.command.option.amount.description")
                ),
                default=0, min_value=50, max_value=10000
            )
    ) -> None:
        await TicTacToeCommand(self).tic_tac_toe(interaction, member=member, amount=amount)


def setup(bot: "ChisatoBot") -> None:
    bot.add_cog(Games(bot))

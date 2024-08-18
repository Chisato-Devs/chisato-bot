from disnake import Member, ApplicationCommandInteraction

from utils.basic import EmbedErrorUI, CogUI, EmbedUI, IntFormatter
from utils.handlers.economy.games.tictactoe.views import Game
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/economy/games.py")


class TicTacToeCommand:
    def __init__(self, cog: CogUI) -> None:
        self.bot = cog.bot

    async def tic_tac_toe(self, interaction: ApplicationCommandInteraction, member: Member | str, amount: int) -> None:
        if isinstance(member, str):
            if amount > 0:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "games.tic_tac_toe.callback.error.not_ai", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            else:
                game = Game(player1=interaction.author, player2=member, bid=0, interaction=interaction)

                await self.bot.databases.economy.in_game(
                    member=interaction.author.id, guild=interaction.guild.id, _set=True
                )
                turn = game.board.get_player_turn()

                embed = EmbedUI(
                    title=_t.get("games.tic_tac_toe.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "games.tic_tac_toe.turn.description", locale=interaction.guild_locale,
                        values=(
                            turn.mention if turn != 'ai'
                            else _t.get("games.tic_tac_toe.ai", locale=interaction.guild_locale),
                        )
                    )
                ).set_footer(text=_t.get("games.tic_tac_toe.for_game", locale=interaction.guild_locale))

                await interaction.response.send_message(embed=embed, view=game)
                return await game.start()

        elif isinstance(member, Member):
            if amount == 0:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "game.error.amount_0_with_member", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            elif member == interaction.author:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "game.error.author_is_member", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            else:
                await self.bot.databases.economy.in_game(
                    member=interaction.author.id, guild=interaction.guild.id, _set=True
                )
                await interaction.response.send_message(
                    embed=EmbedUI(
                        title=_t.get("games.tic_tac_toe.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "games.tic_tac_toe.duel_for", locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, member.mention,
                                IntFormatter(amount).format_number(), amount
                            )
                        )
                    ), view=Game.Confirm(
                        interaction=interaction, bot=self.bot, author=interaction.author,
                        player2=member, bid=amount
                    )
                )

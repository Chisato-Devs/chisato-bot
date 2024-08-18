import string
from asyncio import sleep
from random import choices
from typing import TYPE_CHECKING

from disnake import ApplicationCommandInteraction, Member, ui, MessageInteraction, Forbidden, NotFound, Guild, Locale
from disnake.errors import HTTPException

from utils.basic import EmbedUI, EmbedErrorUI, View, IntFormatter
from utils.consts import REGULAR_CURRENCY, SUCCESS_EMOJI, ERROR_EMOJI
from utils.consts import TOES_EMOJIS
from utils.i18n import ChisatoLocalStore
from ..engine import Board, MinimaxEngine
from ..engine.enums import Symbol

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load("./cogs/economy/games.py")


def generate_turn_embed(turn: str | Member, loc: Locale | str) -> EmbedUI:
    return EmbedUI(
        title=_t.get("games.tic_tac_toe.title", locale=loc),
        description=_t.get(
            "games.tic_tac_toe.turn.description", locale=loc,
            values=(
                turn.mention if turn != 'ai'
                else _t.get("games.tic_tac_toe.ai", locale=loc),
            )
        )
    ).set_footer(text=_t.get("games.tic_tac_toe.for_game", locale=loc))


class Game(View):
    class IncludeButton(ui.Button):
        __slots__ = (
            "_bot", "number", "loc",
            "toe", "last_view",
            "_p1", "_p2", "__b",
            "_guild", "_is_game"
        )

        def __init__(self, board: Board, toe: tuple, _v: "Game", bot: "ChisatoBot", is_game: bool = True) -> None:
            self._bot = bot

            self._guild = _v.guild
            self.number = toe[1]
            self.toe = toe[1]

            self.loc = _v._interaction.guild_locale
            self.last_view = _v

            self._p1 = board.player1
            self._p2 = board.player2
            self.__b = board

            self._is_game = is_game

            alt_id = "".join(choices(string.ascii_letters + string.digits, k=21))
            if is_game:
                super().__init__(
                    emoji=TOES_EMOJIS.get(toe[1], '<:empty:1183500325517279244>'), row=toe[0][1],
                    custom_id=alt_id if str(toe[1]) == 'X' or str(toe[1]) == 'O' else toe[1],
                    disabled=True if toe[1] == 'X' or toe[1] == 'O' else False
                )
            else:
                super().__init__(
                    emoji='<:Flag:1178683705208868965>', row=toe[0][1],
                    custom_id=alt_id, disabled=False, label=_t.get(
                        "game.fool", locale=self.loc
                    )
                )

        async def win_logic(self, interaction: MessageInteraction) -> bool:
            if self.__b.is_gameover():
                view = self.last_view.off()
                if self.__b.winner():
                    if "ai" not in [self.__b.player1, self.__b.player2]:
                        await self._bot.databases.economy.pay(
                            member=self.__b.winner().id,
                            member_pay=self._p2.id if self.__b.winner() != self._p2 else self._p1.id,
                            guild=interaction.guild.id,
                            amount=self.__b.bid
                        )

                        await self._bot.databases.transactions.add(
                            guild=interaction.guild.id, user=self.__b.winner().id, typing=False,
                            amount=self.__b.bid, locale_key="game.win.tic_tac_toe.transactions"
                        )
                        await self._bot.databases.transactions.add(
                            guild=interaction.guild.id, typing=True,
                            user=self._p2.id if self.__b.winner() != self._p2 else self._p1.id,
                            amount=self.__b.bid, locale_key="game.lose.tic_tac_toe.transactions"
                        )

                    isis = isinstance(self.__b.winner(), Member)
                    try:
                        await interaction.edit_original_response(
                            embed=EmbedUI(
                                title=_t.get("games.tic_tac_toe.title", locale=self.loc),
                                description=_t.get(
                                    "game.win.tic_tac_toe.embed.description", locale=self.loc,
                                    values=(
                                        self.__b.winner().mention if isis else _t.get(
                                            "games.tic_tac_toe.ai", locale=interaction.guild_locale
                                        ),
                                        self.__b.bid, REGULAR_CURRENCY
                                    )
                                )
                            ), view=view
                        )
                    except NotFound:
                        pass
                elif self.__b.is_draw():
                    try:
                        await interaction.edit_original_response(
                            embed=EmbedUI(
                                title=_t.get("games.tic_tac_toe.title", locale=self.loc),
                                description=_t.get("game.draw.tic_tac_toe.embed.description", locale=self.loc)
                            ), view=view
                        )
                    except NotFound:
                        pass

                await self._bot.databases.economy.in_game(
                    member=self._p1.id if self._p2 == "ai" else self._p2.id, guild=self._guild.id, _set=False
                )
                await self._bot.databases.economy.in_game(
                    member=self._p2.id if self._p1 == "ai" else self._p1.id, guild=self._guild.id, _set=False
                )

                return True

        async def make_ai_move(self, interaction: MessageInteraction) -> None:
            if self.__b.get_player_turn() == "ai":
                await sleep(2)
                self.__b.move(self.last_view.ai.evaluate_best_move(self.__b))

                turn = self.__b.get_player_turn()
                try:
                    await interaction.edit_original_response(
                        embed=generate_turn_embed(turn, interaction.guild.preferred_locale),
                        view=self.last_view.generate()
                    )
                except NotFound:
                    pass

        async def callback(self, interaction: MessageInteraction) -> None:
            if self._is_game:
                self.__b.move(int(self.custom_id))
                turn = self.__b.get_player_turn()
                await interaction.response.edit_message(
                    embed=generate_turn_embed(turn, interaction.guild.preferred_locale),
                    view=self.last_view.generate()
                )

                if await self.win_logic(interaction):
                    return None

                if self._p1 == "ai" or self._p2 == "ai":
                    try:
                        await self.make_ai_move(interaction)
                    except TypeError:
                        pass
                    except HTTPException:
                        pass
                    finally:
                        await self.win_logic(interaction)
            else:
                await self.last_view.drawn(interaction.author)

                surrender = interaction.author
                winner = {
                    self.__b.player1: self.__b.player2,
                    self.__b.player2: self.__b.player1
                }[surrender]

                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("games.tic_tac_toe.title", locale=interaction.guild.preferred_locale),
                        description=_t.get(
                            "game.fool.tic_tac_toe.embed.description",
                            locale=interaction.guild.preferred_locale,
                            values=(
                                surrender.mention,
                                winner.mention
                                if winner != 'ai' else
                                _t.get(
                                    "game.fool.tic_tac_toe.embed.description.part.1",
                                    locale=interaction.guild.preferred_locale
                                ),
                                IntFormatter(self.__b.bid).format_number(), self.__b.bid
                            )
                        )
                    ), view=self.last_view.off()
                )

    __slots__ = (
        "_bot", "_interaction", "board", "loc",
        "ai", "_p1", "_p2", "ended", "tics"
    )

    def __init__(
            self, player1: Member, player2: Member | str, bid: int,
            interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> None:
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._interaction = interaction

        self.loc = interaction.guild_locale
        self.board = Board([player2, player1], bid=bid)
        self.ai = MinimaxEngine(Symbol.CIRCLE, Symbol.CROSS, (self.board.size ** self.board.size) - 1)

        self._p1 = self.board.player1
        self._p2 = self.board.player2
        self.tics = {}

        self.ended = False

        super().__init__(timeout=360)
        self.generate()

    @property
    def guild(self) -> Guild:
        return self._interaction.guild

    async def drawn(self, player: Member = None) -> None:
        if "ai" not in [self.board.player1, self.board.player2]:
            turn = self.board.get_player_turn() if not player else player

            await self._bot.databases.economy.remove_balance_no_limit(
                guild=self._interaction.guild.id, member=turn.id,
                amount=self.board.bid
            )

            await self._bot.databases.economy.add_balance(
                guild=self._interaction.guild.id, amount=self.board.bid,
                member=self._p2.id if turn != self._p2 else self._p1.id
            )

            await self._bot.databases.transactions.add(
                guild=self._interaction.guild.id, user=self._p2.id if turn != self._p2 else self._p1.id,
                typing=False, amount=self.board.bid, locale_key="game.win.tic_tac_toe.transactions"
            )
            await self._bot.databases.transactions.add(
                guild=self._interaction.guild.id, user=turn.id, typing=True,
                amount=self.board.bid, locale_key="game.lose.tic_tac_toe.transactions"
            )

            await self._bot.databases.economy.in_game(
                member=self._p1.id, guild=self._interaction.guild.id, _set=False
            )
            await self._bot.databases.economy.in_game(
                member=self._p2.id, guild=self._interaction.guild.id, _set=False
            )

            return

        await self._bot.databases.economy.in_game(
            member=self._p1.id if self._p2 == "ai" else self._p2.id,
            guild=self._interaction.guild.id, _set=False
        )

    async def on_timeout(self) -> None:
        if not self.ended:
            self.off()
            await self.drawn()

            try:
                await self._interaction.edit_original_response(view=self)
            except Forbidden:
                pass
            except NotFound:
                pass
            except HTTPException:
                pass

    async def start(self) -> None:
        if self._p1 == "ai" or self._p2 == "ai":
            if self.board.get_player_turn() == "ai":
                self.board.move(self.ai.evaluate_best_move(self.board))

                turn = self.board.get_player_turn()
                await self._interaction.edit_original_response(
                    embed=generate_turn_embed(
                        turn, self._interaction.guild.preferred_locale
                    ),
                    view=self.generate()
                )

    def generate(self) -> "Game":
        self.clear_items()
        self.tics.clear()

        for _is in self.board.get():
            self.add_item(this := self.IncludeButton(board=self.board, toe=_is, _v=self, bot=self._bot))
            self.tics[_is] = this

        self.add_item(
            self.IncludeButton(
                board=self.board, toe=((3, 3), 'not_game'), _v=self, bot=self._bot, is_game=False
            )
        )

        return self

    def off(self) -> "Game":
        for child in self.children:
            child.disabled = True
        self.ended = True

        return self

    @ui.button(label='Крестик-Нолик', custom_id='any_custom_id_HskGo2191d')
    async def _func_(self, *args, **kwargs) -> ...:
        ...

    async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
        if interaction.author not in [self.board.player1, self.board.player2]:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get("game.tic_tac_toe.error.its_not_you", locale=self.loc), interaction.author
                ),
                ephemeral=True
            )
            return False

        if interaction.component.custom_id == "surrender_tic_tac_toe":
            return True

        try:
            if interaction.author.id == self.board.get_player_turn().id:
                return True
            else:
                raise AttributeError
        except AttributeError:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get("game.tic_tac_toe.error.its_not_you_turn", locale=self.loc),
                    interaction.author
                ), ephemeral=True
            )
            return False

    class Confirm(View):
        __slots__ = (
            "_bot", "_interaction", "_bid",
            "_end", "_author", "_player2", "loc"
        )

        def __init__(
                self, interaction: ApplicationCommandInteraction, bot: "ChisatoBot",
                author: Member, player2: Member, bid: int
        ) -> None:
            self._bot = bot
            self._interaction = interaction

            self._end = False

            self._author = author
            self._player2 = player2

            self._bid = bid
            self.loc = interaction.guild_locale

            super().__init__(timeout=300, store=_t, interaction=interaction)

        async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
            members = [self._player2, self._author]
            if interaction.component.custom_id == "tic-tac-toe_confirm":
                members.pop()

            if interaction.author not in members:
                return await self.send_error_message(interaction)

            return True

        async def on_timeout(self) -> None:
            if not self._end:
                for child in self.children:
                    child.disabled = True

                try:
                    await self._interaction.edit_original_response(view=self)
                except Forbidden:
                    pass
                except NotFound:
                    pass
                except HTTPException:
                    pass

        @ui.button(
            label="game.tic_tac_toe.success.label", emoji=SUCCESS_EMOJI,
            row=0, custom_id="tic-tac-toe_confirm"
        )
        async def confirm(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            if not await self._bot.databases.economy.money_check(
                    guild=interaction.guild.id, check_rate=self._bid,
                    check_member=interaction.author.id
            ):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "game.error.not_enough_money",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            if not await self._bot.databases.economy.money_check(
                    guild=interaction.guild.id, check_rate=self._bid,
                    check_member=self._author.id
            ):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "game.error.not_enough_money_author",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

            game = Game(player1=self._author, player2=interaction.author, bid=self._bid, interaction=interaction)
            turn = game.board.get_player_turn()

            await self._bot.databases.economy.in_game(
                member=interaction.author.id, guild=interaction.guild.id, _set=True
            )

            await interaction.response.send_message(
                embed=generate_turn_embed(
                    turn, interaction.guild.preferred_locale
                ),
                view=game
            )

        @ui.button(
            label="game.tic_tac_toe.decline.label", emoji=ERROR_EMOJI,
            row=1, custom_id="tic-tac-toe_decline"
        )
        async def decline(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            if interaction.author.id == self._author.id:
                await self._bot.databases.economy.in_game(
                    member=interaction.author.id, guild=self._interaction.guild.id,
                    _set=False
                )

                return await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("games.tic_tac_toe.title", locale=self.loc),
                        description=_t.get(
                            "game.tic_tac_toe.decline.embed.description", locale=self.loc,
                            values=(
                                self._author.mention, self._player2.mention,
                                IntFormatter(self._bid).format_number(), self._bid
                            )
                        )
                    ),
                    view=None
                )

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("games.tic_tac_toe.title", locale=self.loc),
                    description=_t.get(
                        "game.tic_tac_toe.decline.embed.description.is_not_author", locale=self.loc,
                        values=(
                            self._player2.mention, self._author.mention,
                            IntFormatter(self._bid).format_number(), self._bid
                        )
                    )
                ), view=None
            )

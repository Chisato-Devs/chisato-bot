from typing import Callable

from disnake import MessageInteraction, ApplicationCommandInteraction, Locale, Forbidden, HTTPException, ui
from disnake.ui import Item

from utils.basic import EmbedUI, EmbedErrorUI, View
from utils.basic.services.draw import DrawService
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI
from utils.dataclasses import CardItem
from utils.exceptions import CardNotInTrade
from utils.handlers.entertainment.cards.consts import STAR
from utils.handlers.entertainment.cards.generators import Card
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")


class OfferUI(View):
    def __init__(
            self,
            interaction: ApplicationCommandInteraction | MessageInteraction,
            cards: list[CardItem]
    ) -> None:
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._interaction: ApplicationCommandInteraction | MessageInteraction = interaction
        self._cards = cards

        self._end: bool = False

        super().__init__(
            store=_t,
            interaction=interaction,
            author=interaction.author,
            timeout=300
        )

        self.wait_data = {
            "embed": EmbedUI(
                title=_t.get("cards.wait.title", locale=interaction.guild_locale)
            ),
            "view": None,
            "attachments": []
        }

    async def configure(self) -> None:
        try:
            side, trade_id = await self._bot.databases.cards.is_your_side(self._cards[0])
        except ValueError:
            try:
                await self._interaction.edit_original_response(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "cards.trade.error.not_found_offer",
                            locale=self._interaction.guild_locale
                        ),
                        member=self._interaction.author
                    )
                )
            except Forbidden:
                pass
            except HTTPException:
                pass
            finally:
                return

        self.decline.label = _t.get(
            "cards.trades.ui.decline.label",
            locale=self._interaction.guild_locale
        )
        match side:
            case True:
                self.remove_item(self.accept)
                self.decline.label = _t.get(
                    "cards.trades.ui.decline_is_side.label",
                    locale=self._interaction.guild_locale
                )
            case False:
                self.decline.label = _t.get(
                    "cards.trades.ui.decline.label",
                    locale=self._interaction.guild_locale
                )
                self.accept.label = _t.get(
                    "cards.trades.ui.accept.label",
                    locale=self._interaction.guild_locale
                )

    async def owner_alert(self, embed: EmbedUI, owner: int) -> None:
        if user := await self._bot.get_or_fetch_user(owner):
            try:
                await user.send(embed=embed)
            except Forbidden:
                pass
            except HTTPException:
                pass

    def _generate_to_user(self, _l: Locale) -> tuple:
        return (
            self._cards[1].uid,
            _t.get(self._cards[1].name_key, locale=_l),
            STAR * self._cards[1].stars_count,
            self._cards[0].uid,
            _t.get(self._cards[0].name_key, locale=_l),
            STAR * self._cards[0].stars_count
        )

    def _generate_values(self, _l: Locale) -> tuple:
        return (
            self._cards[0].uid,
            _t.get(self._cards[0].name_key, locale=_l),
            STAR * self._cards[0].stars_count,
            self._cards[1].uid,
            _t.get(self._cards[1].name_key, locale=_l),
            STAR * self._cards[1].stars_count
        )

    async def _create_decline_embed(
            self,
            _l: Locale,
            generate_func: Callable[[Locale], tuple],
            *, _draw: bool = False
    ) -> EmbedUI:
        embed = EmbedUI(
            title=ERROR_EMOJI + _t.get(
                "cards.trades.ui.decline.offer_decline", _l
            ),
            description=_t.get(
                "cards.trades.ui.decline.other_owner.alert", _l,
                values=generate_func(_l)
            )
        )
        if _draw and await DrawService(self._bot.session).get_status():
            embed.set_image(
                file=await Card.draw_trade_image(
                    [self._cards[1], self._cards[0]], bot=self._bot
                )
            )

        return embed

    async def on_error(self, error: Exception, item: Item, interaction: MessageInteraction) -> None:
        error = getattr(error, "original", error)
        if isinstance(error, CardNotInTrade):
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.not_actuality_offer",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        else:
            await super().on_error(error, item, interaction)

    @ui.button(label="DECLINE", custom_id="cards.trades.ui.decline", emoji=ERROR_EMOJI)
    async def decline(self, _, interaction: MessageInteraction) -> None:
        self._end = True

        await interaction.response.edit_message(
            embed=(
                await self._create_decline_embed(
                    interaction.guild_locale, self._generate_values
                )
            ).set_image(
                interaction.message.embeds[0].image.url
            ),
            view=None, attachments=[]
        )
        await self._bot.databases.cards.remove_trade_from_id(
            (await self._bot.databases.cards.is_your_side(self._cards[0]))[1]
        )

        await self.owner_alert(
            embed=await self._create_decline_embed(
                interaction.guild_locale, self._generate_to_user, _draw=True
            ),
            owner=self._cards[1].owner
        )

    async def _create_access_embed(
            self, _l: Locale, generate_func: Callable[
                [Locale], tuple
            ], *, _draw: bool = False
    ) -> EmbedUI:
        embed = EmbedUI(
            title=SUCCESS_EMOJI + _t.get(
                "cards.trades.ui.access.offer_access", _l
            ),
            description=_t.get(
                "cards.trades.ui.access.other_owner.alert", _l,
                values=generate_func(_l)
            )
        )
        if _draw and await DrawService(self._bot.session).get_status():
            embed.set_image(
                file=await Card.draw_trade_image(
                    [self._cards[1], self._cards[0]], bot=self._bot
                )
            )

        return embed

    @ui.button(label="ACCEPT", custom_id="cards.trades.ui.accept", emoji=SUCCESS_EMOJI)
    async def accept(self, _, interaction: MessageInteraction) -> None:
        self._end = True

        await interaction.response.edit_message(
            embed=(
                await self._create_access_embed(
                    interaction.guild_locale, self._generate_values
                )
            ).set_image(
                interaction.message.embeds[0].image.url
            ),
            view=None,
            attachments=[]
        )

        await self._bot.databases.cards.trade_success(
            (await self._bot.databases.cards.is_your_side(self._cards[0]))[1]
        )

        await self.owner_alert(
            embed=await self._create_access_embed(
                interaction.guild_locale, self._generate_to_user,
                _draw=True
            ),
            owner=self._cards[1].owner
        )

    @classmethod
    async def generate(
            cls,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            cards: list[CardItem]
    ) -> "OfferUI":
        await (self := cls(interaction, cards)).configure()
        return self

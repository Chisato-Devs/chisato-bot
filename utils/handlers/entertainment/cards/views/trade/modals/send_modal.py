from typing import Optional, TYPE_CHECKING

from disnake import ModalInteraction, ui, MessageInteraction

from utils.basic import View, EmbedErrorUI, EmbedUI
from utils.basic.services.draw import DrawService
from utils.dataclasses import CardItem
from utils.handlers.entertainment.cards.consts import STAR
from utils.handlers.entertainment.cards.generators import Embeds, Card
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    pass

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")

__all__ = (
    "ModalTrades",
)


class ModalTrades(ui.Modal):
    def __init__(
            self,
            interaction: MessageInteraction,
            card: CardItem,
            last_view: "Pagination"
    ) -> None:
        self._interaction = interaction
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._last_view = last_view

        self._card = card

        super().__init__(
            title=_t.get(
                "cards.trade.modal.title",
                locale=interaction.guild_locale
            ),
            components=[
                ui.TextInput(
                    label=_t.get(
                        "cards.trade.modal.components.1.label",
                        locale=interaction.guild_locale
                    ),
                    placeholder="0",
                    custom_id="card_id"
                )
            ]
        )

    @staticmethod
    def _can_int(_a: int | str) -> Optional[int]:
        try:
            return int(_a)
        except ValueError:
            return None

    async def get_card(self, card_name: str) -> Optional[CardItem]:
        if not (card := self._can_int(card_name)):
            return None
        if not (card_item := await self._bot.databases.cards.get_card_from_id(card)):
            return None

        return card_item

    class IncludeButton(View):
        def __init__(
                self,
                interaction: ModalInteraction,
                cards: list[CardItem],
                to_trade: "Pagination"
        ) -> None:
            self._bot: "ChisatoBot" = interaction.bot  # type: ignore
            self._interaction = interaction
            self._cards = cards
            self._end = False
            self._to_trade = to_trade

            super().__init__(timeout=300, store=_t, interaction=interaction, author=interaction.author)

        @ui.button(
            emoji="<:send:1199422590389866516>",
            label="cards.trade.button.trade_send.confirm",
            custom_id="cards.trade.confirm.confirm.button"
        )
        async def confirm(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            if await self._bot.databases.cards.check_in_trade(self._cards[0].uid):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "cards.trade.error.in_your_side.in_trade",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            if await self._bot.databases.cards.check_in_trade(self._cards[1].uid):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "cards.trade.error.in_other_side.in_trade",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

            await self._bot.databases.cards.trade_send(*self._cards)
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("cards.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "cards.trade.success.sent",
                        locale=interaction.guild_locale
                    )
                ),
                ephemeral=True
            )
            await interaction.message.delete()

        @ui.button(
            label="cards.button.back",
            emoji="<:ArrowLeft:1114648737730539620>",
            custom_id="cards.trade.confirm.back.button"
        )
        async def back(self, _, interaction: MessageInteraction) -> None:
            self._end = True
            cards = await self._bot.databases.cards.get_cards(interaction.author)

            if not cards:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "cards.trade.error.in_your_side.doesnt_have_cards",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

            await self.custom_defer(interaction)
            embeds, from_page = await Embeds.generate_with_interact(
                interaction, cards, EmbedUI(
                    title=_t.get(
                        "cards.trade.sent.title",
                        locale=interaction.guild_locale
                    )
                )
            )

            self._to_trade.embeds = embeds
            self._to_trade.from_page = from_page
            self._to_trade.configure()

            await interaction.edit_original_response(embed=embeds[0], view=self._to_trade)

    async def callback(self, interaction: ModalInteraction, /) -> None:
        if not (card_item := await self.get_card(interaction.text_values["card_id"])):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.not_found_id",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        if card_item.owner == interaction.author.id:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.in_your_side.is_your_card",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        if await self._bot.databases.cards.check_in_trade(self._card.uid):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.in_your_side.in_trade",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        if await self._bot.databases.cards.check_in_trade(card_item.uid):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.in_other_side.in_trade",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await self._last_view.custom_defer(interaction)

        # noinspection DuplicatedCode
        cards = [self._card, card_item]
        embed = EmbedUI(
            title=_t.get(
                "cards.trades.title.create_offer",
                locale=interaction.guild_locale
            ),
            description=_t.get(
                "cards.trades.bio.description",
                locale=interaction.guild_locale,
                values=(
                    cards[0].uid,
                    _t.get(cards[0].name_key, locale=interaction.guild_locale),
                    STAR * cards[0].stars_count,
                    cards[1].uid,
                    _t.get(cards[1].name_key, locale=interaction.guild_locale),
                    STAR * cards[1].stars_count
                )
            )
        )

        if await DrawService(self._bot.session).get_status():
            embed.set_image(
                file=await Card.draw_trade_image(cards, bot=self._bot)
            )

        await interaction.edit_original_response(
            embed=embed,
            view=self.IncludeButton(interaction, cards, self._last_view)
        )

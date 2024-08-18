import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING

from asyncpg import Record
from disnake import MessageInteraction, ui, ApplicationCommandInteraction, SelectOption

from utils.basic import View, EmbedErrorUI, EmbedUI
from utils.basic.services.draw import DrawService
from utils.dataclasses import CardItem
from utils.exceptions import CardNotInTrade
from utils.handlers.entertainment.cards.consts import STAR
from utils.handlers.entertainment.cards.generators import Embeds, Card
from utils.handlers.entertainment.cards.views.pagination import Pagination
from utils.handlers.entertainment.cards.views.trade.modals import ModalTrades
from utils.handlers.entertainment.cards.views.trade.offer import OfferUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    pass

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")


class CardTradeMenu(View):
    def __init__(self, interaction: ApplicationCommandInteraction) -> None:
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._end = False
        self._interaction = interaction

        super().__init__(
            interaction=interaction, store=_t,
            author=interaction.author, timeout=240
        )

    @staticmethod
    async def trade_send_logic(
            self: "Pagination",
            select: ui.Select,
            interaction: MessageInteraction
    ) -> None:
        await interaction.response.send_modal(
            ModalTrades(
                interaction, self._from_page[self.page][int(select.values[0])], self
            )
        )

    @staticmethod
    def option_create_offer_button(
            self: "Pagination",
            position: int,
            card: CardItem
    ) -> SelectOption:
        _l = self._interaction.guild_locale

        return SelectOption(
            label=_t.get(
                "cards.inventory_select.label", locale=_l,
                values=(str(position),)
            ),
            emoji=STAR,
            description=_t.get(
                "cards.inventory_select.description", locale=_l,
                values=(
                    _t.get(card.name_key, locale=_l), '⭐' * card.stars_count
                )
            ),
            value=str(position)
        )

    @ui.button(
        label="cards.trades.offers.button.try_offer", row=0,
        custom_id="cards.view.trade_send.button",
        emoji="<:cloud_outgoing:1196039990816292944>"
    )
    async def offer_button(self, _, interaction: MessageInteraction) -> None:
        self._end = True

        if not (cards := await self._bot.databases.cards.get_cards(interaction.author)):
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

        view = await Pagination.generate(
            interaction, embeds, from_page,
            callback=self.trade_send_logic,
            option_create=self.option_create_offer_button,
            placeholder_key="cards.pagination.placeholder.offer_send"
        )

        await interaction.edit_original_response(
            embed=embeds[0], view=view
        )

    async def generate_offers(
            self,
            trades_data: list[Record]
    ) -> tuple[list[EmbedUI], defaultdict[any, defaultdict]]:
        embeds = []
        text = ""
        _l = self._interaction.guild_locale
        from_page = defaultdict(defaultdict)

        _dict_rares = _t.get("cards.rares", _l)
        _title = _t.get("cards.activity_offers.title", _l)
        _text = _t.get("cards.generator.offers.text", _l)

        for i, trade_info in enumerate(trades_data, 1):
            cards: tuple[CardItem, CardItem] = await asyncio.gather(
                self._bot.databases.cards.get_card_from_id(trade_info[1]),
                self._bot.databases.cards.get_card_from_id(trade_info[2])
            )

            offer_item, to_offer_item = (
                cards[0], cards[1]
            ) if cards[0].owner == self._interaction.author.id else (
                cards[1], cards[0]
            )

            text += _text.format(
                str(i), trade_info[0],

                _t.get(offer_item.name_key, _l),
                _dict_rares[offer_item.rarity],
                STAR * offer_item.stars_count,

                _t.get(to_offer_item.name_key, _l),
                _dict_rares[to_offer_item.rarity],
                STAR * to_offer_item.stars_count
            )

            from_page[i // 5 if i % 5 == 0 else i // 5 + 1][i] = [offer_item, to_offer_item]

            if i % 5 == 0 or i == len(trades_data):
                embeds.append(EmbedUI(title=_title, description=text))
                text = ""

        return embeds, from_page

    @staticmethod
    async def callback_select_offer(
            self: "Pagination",
            select: ui.StringSelect,
            interaction: MessageInteraction
    ) -> None:
        cards = self._from_page[self.page][int(select.values[0])]

        try:
            view = await OfferUI.generate(
                interaction=interaction, cards=cards
            )

        except CardNotInTrade:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.trade.error.not_actuality_offer",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await interaction.response.edit_message(**{
            "embed": EmbedUI(
                title=_t.get("cards.wait.title", locale=interaction.guild_locale)
            ),
            "view": None,
            "attachments": []
        })

        # noinspection DuplicatedCode
        embed = EmbedUI(
            title=_t.get(
                "cards.offer.label",
                locale=interaction.guild_locale,
                values=(select.values[0],)
            ),
            description="\n\n" + _t.get(
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
            embed.set_image(file=await Card.draw_trade_image(cards, bot=self._bot))

        await interaction.edit_original_response(embed=embed, view=view)

    @staticmethod
    def option_create_check(
            self: "Pagination", position: int, cards: list[CardItem]
    ) -> SelectOption:
        _l = self._interaction.guild_locale
        desc = "{0} ({1}) -> {2} ({3})"

        return SelectOption(
            label=_t.get(
                "cards.offer.label", _l,
                (str(position),)
            ),
            value=str(position),
            description=desc.format(
                _t.get(cards[0].name_key, _l), '⭐' * cards[0].stars_count,
                _t.get(cards[1].name_key, _l), '⭐' * cards[0].stars_count
            )
        )

    @ui.button(
        label="cards.trades.offers.button.activity", row=1,
        custom_id="cards.views.trades.check_offers",
        emoji="<:cloud_incomming:1196039992250728448>"
    )
    async def check_offers(self, _, interaction: MessageInteraction) -> None:
        self._end = True
        if trades_data := await self._bot.databases.cards.get_trades(interaction.author.id):
            await interaction.response.defer()
            embeds, from_page = await self.generate_offers(
                list(sorted(trades_data, key=lambda x: x[3]))
            )

            view = await Pagination.generate(
                interaction, embeds, from_page,
                callback=self.callback_select_offer,
                option_create=self.option_create_check,
                placeholder_key="cards.pagination.placeholder.select_offer",
                remove_filter=True,

            )

            await interaction.edit_original_response(
                embed=embeds[0], view=view
            )
        else:
            await interaction.response.send_message(
                **{
                    "embed": EmbedErrorUI(
                        description=_t.get(
                            "cards.trade.error.doesnt_have_activity_offer",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    "ephemeral": True
                }
            )

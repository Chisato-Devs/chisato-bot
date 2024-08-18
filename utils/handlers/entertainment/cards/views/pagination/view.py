from collections import defaultdict
from typing import TYPE_CHECKING, Callable, TypeVar

from asyncpg import Record
from disnake import MessageInteraction, ApplicationCommandInteraction, SelectOption, ui

from utils.basic import EmbedUI
from utils.dataclasses import CardItem
from utils.handlers.entertainment.cards.generators import Embeds
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")
T = TypeVar("T")

if TYPE_CHECKING:
    PAGINATION_CALLBACK_FUNC_TYPE: Callable[
        ["Pagination", ui.Select, ApplicationCommandInteraction | MessageInteraction], T
    ]
    PAGINATION_OPTION_FUNC_TYPE: Callable[
                                     ["Pagination", int, CardItem], SelectOption
                                 ] | Callable[
                                     ["Pagination", int, list[CardItem]], SelectOption
                                 ]


class Pagination(PaginatorView):
    def __init__(
            self, interaction: ApplicationCommandInteraction | MessageInteraction,
            embeds: list[EmbedUI],
            from_page: defaultdict[any, defaultdict],
            callback: "PAGINATION_CALLBACK_FUNC_TYPE",
            option_create: "PAGINATION_OPTION_FUNC_TYPE",
            placeholder_key: str,
            remove_filer: bool = False
    ) -> None:
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._interaction = interaction
        self._from_page = from_page
        self._rares = _t.get("cards.rares", locale=interaction.guild_locale)
        self.end = False

        self._config = {
            "callback": callback,
            "placeholder": placeholder_key,
            "option": option_create
        }

        super().__init__(
            store=_t,
            author=interaction.author,
            interaction=interaction,
            timeout=300,
            footer=True,
            embeds=embeds,
            delete_button=True
        )

        if remove_filer:
            self.remove_item(self.filter)  # type: ignore

        self.configure()

    @property
    def from_page(self) -> defaultdict[any, defaultdict]:
        return self._from_page

    @from_page.setter
    def from_page(self, value: defaultdict[any, defaultdict]) -> None:
        self._from_page = value

    async def before_edit_message(self, interaction: MessageInteraction) -> any:
        self.end = True
        self.configure()

    def configure(self) -> None:
        self.select.placeholder = _t.get(
            self._config["placeholder"],
            locale=self._interaction.guild_locale
        )

        self.select.options = [
            self._config["option"](self, i, card_item)
            for i, card_item in self._from_page[self.page].items()
        ]

    @classmethod
    async def generate(
            cls,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            embeds: list[EmbedUI],
            from_page: defaultdict[any, defaultdict],
            callback: "PAGINATION_CALLBACK_FUNC_TYPE",
            option_create: "PAGINATION_OPTION_FUNC_TYPE",
            placeholder_key: str,
            remove_filter: bool = False
    ) -> "Pagination":
        return cls(
            interaction=interaction,
            embeds=embeds,
            from_page=from_page,
            callback=callback,
            option_create=option_create,
            placeholder_key=placeholder_key,
            remove_filer=remove_filter
        )

    async def set_filer(self, filer_id: str) -> list[Record]:
        cards = await self._bot.databases.cards.get_cards(self._interaction.author)

        match filer_id:
            case "4":
                return list(sorted(
                    cards,
                    key=lambda x: self._bot.databases.cards._cards_config[x[4]]["priority"]
                ))
            case "0":
                return list(sorted(cards, key=lambda x: x[0], reverse=True))
            case "0.reverse":
                return list(sorted(cards, key=lambda x: x[0]))
            case "2":
                return list(sorted(cards, key=lambda x: x[2]))
            case _:
                return cards

    @ui.select(
        placeholder="cards.trade.filter.label",
        custom_id="cards.select.filter", row=3,
        options=[
            SelectOption(
                label="cards.trade.filter.option.date",
                emoji="<:Calender:1200763346480279604>",
                value="2"
            ),
            SelectOption(
                label="cards.trade.filter.option.rarity",
                emoji="<:Star2:1131445020210245715>",
                value="4"
            ),
            SelectOption(
                label="cards.trade.filter.option.id_up",
                emoji="<:up:1200763344974524488>",
                value="0.reverse"
            ),
            SelectOption(
                label="cards.trade.filter.option.id_down",
                emoji="<:down:1200763349646970890>",
                value="0"
            )
        ]
    )
    async def filter(self, select: ui.Select, interaction: MessageInteraction) -> None:
        self.end = True
        await self.custom_defer(interaction)

        embeds, from_page = await Embeds.generate_with_interact(
            interaction=interaction,
            cards=await self.set_filer(select.values[0]),
            example_embed=EmbedUI(
                title=interaction.message.embeds[0].title
            )
        )

        for child in self.children:
            child.disabled = False

        self.embeds = embeds
        self.set_footers(embeds, self._interaction.guild_locale)
        self.from_page = from_page
        self.page = 1

        self.configure()

        await interaction.edit_original_response(
            embed=embeds[0], view=self
        )

    @ui.select(
        placeholder="SELECT CARD",
        custom_id="cards.select.card",
        options=[SelectOption(label="Сдохло")],
        row=2
    )
    async def select(self, select: ui.Select, interaction: MessageInteraction) -> None:
        self.end = True
        return await self._config["callback"](self, select, interaction)

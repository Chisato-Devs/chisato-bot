import asyncio
from datetime import datetime
from typing import (
    TYPE_CHECKING
)

from disnake import (
    ApplicationCommandInteraction,
    ui,
    MessageInteraction,
    SelectOption,
    Localized, Member
)
from disnake.ext.commands import Context
from disnake.ext.tasks import loop
from disnake.utils import format_dt

from utils.basic import (
    CogUI,
    EmbedUI,
    EmbedErrorUI,
    IntFormatter
)
from utils.basic.services.draw import DrawService
from utils.dataclasses import CardItem
from utils.handlers.entertainment.cards.consts import STAR, OPENING_URI
from utils.handlers.entertainment.cards.generators import Card, Embeds
from utils.handlers.entertainment.cards.views.pagination import Pagination
from utils.handlers.entertainment.cards.views.roll import CardRollView
from utils.handlers.entertainment.cards.views.trade.view import CardTradeMenu
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class Cards(CogUI):
    def __init__(self, bot: "ChisatoBot") -> None:
        super().__init__(bot)

        self._checked = False

    @CogUI.slash_command(name="cards")
    async def _cards(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    async def _opening_task(self, interaction: ApplicationCommandInteraction) -> None:
        cards = await self.bot.databases.cards.generate_cards(3)
        async with (DrawService(self.bot.session) as ir):
            try:
                file = await ir.draw_image(
                    "cards_trio",
                    cache=False,
                    firstCardImageName=cards[0].image_key,
                    firstCardRarity=cards[0].rarity,
                    secondCardImageName=cards[1].image_key,
                    secondCardRarity=cards[1].rarity,
                    thirdCardImageName=cards[2].image_key,
                    thirdCardRarity=cards[2].rarity
                )
            except TimeoutError:
                await self.bot.databases.cards.add_rolls(interaction.author, 1)
                await interaction.edit_original_response(
                    embed=EmbedErrorUI(
                        member=interaction.author,
                        description=_t.get(
                            "cards.error.while_opening",
                            locale=interaction.guild_locale
                        )
                    )
                )
                return

        await interaction.edit_original_response(
            embed=EmbedUI()
            .set_image(file=file)
            .set_footer(
                text=_t.get(
                    "cards.opening.footer",
                    locale=interaction.guild_locale
                )
            ),
            view=CardRollView(
                interaction=interaction,
                cards=cards
            )
        )

    @_cards.sub_command(
        name="roll", description=Localized(
            "🃏 Аниме-карточки: покрутить спины",
            data=_t.get("cards.roll.command.description")
        )
    )
    async def roll(self, interaction: ApplicationCommandInteraction) -> None:
        if not self.bot.databases:
            return

        if not await DrawService(self.bot.session).get_status():
            return await interaction.send(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.roll.error.api_error",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        if not await self.bot.databases.cards.can_roll(interaction.author):
            return await interaction.send(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.roll.error.spin_not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await interaction.send(
            embed=EmbedUI(
                title=_t.get(
                    "cards.opening.title",
                    locale=interaction.guild_locale
                )
            ).set_image(url=OPENING_URI)
        )

        asyncio.create_task(self._opening_task(interaction))

    @staticmethod
    async def draw_card_logic(
            self, select: ui.Select,
            interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> None:
        if not await DrawService(self._bot.session).get_status():
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "fun.errors.api_error",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        _l = interaction.guild_locale
        await Card.draw_with_interact(
            interaction,
            (card := self._from_page[self.page][int(select.values[0])]),
            embed_key="cards.inventory.description",
            values=(
                card.uid,
                _t.get(card.male_key, _l),
                format_dt(card.created_timestamp),
                _t.get("cards.rares", _l)[card.rarity],
                _t.get(card.description_key, _l)
            )
        )

    @staticmethod
    def inventory_option_create(
            self: "Pagination",
            position: int,
            card: CardItem
    ) -> SelectOption:
        _l = self._interaction.guild_locale
        return SelectOption(
            label=_t.get(
                "cards.inventory_select.label", _l,
                values=(str(position),)
            ),
            emoji=STAR,
            description=_t.get(
                "cards.inventory_select.description", _l,
                values=(
                    _t.get(card.name_key, _l), '⭐' * card.stars_count
                )
            ),
            value=str(position)
        )

    @_cards.sub_command(
        name="inventory", description=Localized(
            "🃏 Аниме-карточки: посмотреть инвентарь",
            data=_t.get("cards.inventory.command.description")
        )
    )
    async def inventory(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        if not self.bot.databases:
            return

        cards = await self.bot.databases.cards.get_cards(interaction.author)
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

        await interaction.response.defer()
        embeds, from_page = await Embeds.generate_with_interact(
            interaction, cards, EmbedUI(
                title=_t.get("cards.inventory.title", interaction.guild_locale)
            )
        )

        await interaction.edit_original_response(
            embed=embeds[0],
            view=await Pagination.generate(
                embeds=embeds, interaction=interaction,
                from_page=from_page, callback=self.draw_card_logic,
                option_create=self.inventory_option_create,
                placeholder_key="cards.pagination.placeholder.inventory"
            )
        )

    @_cards.sub_command(
        name="trades",
        description=Localized(
            "🃏 Аниме-карточки: Трейды (Обменять/посмотреть предложения)!",
            data=_t.get("cards.trade.command.description")
        )
    )
    async def trades(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get(
                    "cards.trade.menu.title",
                    locale=interaction.guild_locale
                )
            ).set_footer(
                text=_t.get(
                    "cards.trade.menu.footer",
                    locale=interaction.guild_locale
                )
            ),
            view=CardTradeMenu(interaction)
        )

    @loop(minutes=10)
    async def reset_temp_data_loop(self) -> None:
        if not self.bot.databases:
            return

        if datetime.now().hour == 9:
            if not self._checked:
                await self.bot.databases.cards.truncate_timely()
                self._checked = True
        else:
            if self._checked:
                self._checked = False

    @_cards.sub_command(
        name="timely",
        description=Localized(
            "🃏 Аниме-карточки: Получить еженедельные спины!",
            data=_t.get("cards.timely.command.description")
        )
    )
    async def trades(self, interaction: ApplicationCommandInteraction) -> None:
        if await self.bot.databases.cards.get_timely(interaction.author):
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("cards.success.title", locale=interaction.guild_locale),
                    description=_t.get("cards.timely.command.success.callback", locale=interaction.guild_locale)
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "cards.timely.command.error.callback",
                        locale=interaction.guild_locale,
                        values=(
                            IntFormatter(
                                await self.bot.databases.cards.get_time_to_timely(
                                    interaction.author
                                ) - datetime.now().timestamp()
                            ).convert_timestamp(interaction.guild_locale),
                        )
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

    @CogUI.context_command(
        name="give_spin", aliases=["gs"]
    )
    async def give_spin(
            self, ctx: Context, user: Member | str, count: int
    ) -> None:
        await self.bot.databases.cards.add_rolls(user, count)
        await ctx.send("Успешно!")


def setup(bot: "ChisatoBot") -> None:
    return bot.add_cog(Cards(bot))

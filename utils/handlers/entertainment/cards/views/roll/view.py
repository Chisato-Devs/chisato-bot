from disnake import ui, MessageInteraction, ApplicationCommandInteraction, HTTPException, Forbidden
from disnake.utils import format_dt

from utils.basic import EmbedErrorUI, View
from utils.basic.services.draw import DrawService
from utils.dataclasses import CardItem
from utils.handlers.entertainment.cards.generators import Card
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")


class CardRollView(View):
    def __init__(
            self, interaction: ApplicationCommandInteraction,
            cards: list[CardItem]
    ) -> None:
        self._end = False
        self._interaction = interaction
        self._cards = cards
        self._bot: "ChisatoBot" = interaction.bot  # type: ignore

        super().__init__(
            interaction=interaction,
            store=_t,
            author=interaction.author,
            timeout=30
        )

    async def on_timeout(self) -> None:
        if not self._end:
            self.clear_items()

            try:
                await self.backend_logic(
                    interaction=self._interaction, index=max(
                        range(len(self._cards)), key=lambda i: self._cards[i].stars_count
                    )
                )
            except Forbidden:
                pass
            except HTTPException:
                pass

    async def backend_logic(
            self, interaction: MessageInteraction | ApplicationCommandInteraction, index: int
    ) -> None:
        card = await self._bot.databases.cards.create_card(
            card_id=(card := self._cards[index]).card_id,
            user=interaction.author,
            rarity=card.rarity
        )

        if not await DrawService(self._bot.session).get_status():
            return await interaction.response.edit_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "fun.errors.api_error",
                        locale=interaction.guild_locale
                    ) + " " + _t.get(
                        "cards.error.api_part",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await Card.draw_with_interact(
            interaction, card,
            embed_key="cards.dropped.description",
            values=(
                card.uid,
                _t.get(card.male_key, locale=interaction.guild_locale),
                format_dt(card.created_timestamp),
                _t.get("cards.rares", locale=interaction.guild_locale)[card.rarity],
                _t.get(card.description_key, locale=interaction.guild_locale)
            )
        )

    @ui.button(
        label="cards.select_card.label",
        disabled=True, custom_id="cards.select.button"
    )
    async def _select(self, _, interaction: MessageInteraction) -> ...:
        ...

    @ui.button(
        emoji="1️⃣",
        custom_id="cards.select.button.1"
    )
    async def _first(self, _, interaction: MessageInteraction) -> None:
        self._end = True
        await self.backend_logic(interaction, 0)

    @ui.button(
        emoji="2️⃣",
        custom_id="cards.select.button.2"
    )
    async def _second(self, _, interaction: MessageInteraction) -> None:
        self._end = True
        await self.backend_logic(interaction, 1)

    @ui.button(
        emoji="3️⃣",
        custom_id="cards.select.button.3"
    )
    async def _third(self, _, interaction: MessageInteraction) -> None:
        self._end = True
        await self.backend_logic(interaction, 2)

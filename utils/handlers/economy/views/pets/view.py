from disnake import (
    Member,
    HTTPException,
    MessageInteraction,
    ui,
    Embed,
    NotFound,
    Locale
)

from utils.basic import (
    ChisatoBot,
    View,
    EmbedErrorUI,
    EmbedUI
)
from utils.consts import (
    SUCCESS_EMOJI
)
from utils.dataclasses import Pet
from utils.exceptions import (
    NotEnoughMoney,
    AlreadyHavePet
)
from utils.handlers.economy import (
    check_in_fight_button,
    check_in_game_button
)
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/economy/pets.py")


class PetShopPaginator(PaginatorView):
    def __init__(
            self, embeds: list[Embed], author: Member,
            interaction: MessageInteraction,
            from_page: dict[int, Pet]
    ) -> None:
        self._interaction = interaction
        self._end = False
        self._from_page = from_page
        self._bot: "ChisatoBot" = self._interaction.bot  # type: ignore

        super().__init__(
            embeds=embeds, store=_t, footer=True,
            author=author, interaction=interaction
        )

    async def on_timeout(self) -> None:
        if not self._end:
            for child in self.children:
                child.disabled = True

            try:
                await self._interaction.edit_original_response(view=self)
            except NotFound:
                pass
            except HTTPException:
                pass

    @staticmethod
    async def generate(bot: "ChisatoBot", locale: Locale) -> tuple[list[Embed], dict[int, Pet]]:
        from_page = {}
        embeds = []

        pets_dict = _t.get("pets.dict.titles", locale=locale)
        description = _t.get("pets.pet.description", locale=locale)

        for i, pet_item in enumerate(bot.databases.pets.pets_list):
            pet_item: Pet
            from_page[i] = pet_item
            embeds.append(
                EmbedUI(
                    title=pets_dict[pet_item.name],
                    description=description.format(
                        pet_item.power,
                        pet_item.stamina,
                        pet_item.mana,
                        pet_item.cost
                    )
                ).set_thumbnail(
                    pet_item.image_link
                )
            )

        return embeds, from_page

    @ui.button(emoji=SUCCESS_EMOJI, custom_id="pets.pre_buy_button", row=1)
    async def pre_buy(self, _, interaction: MessageInteraction) -> None:
        self._end = True

        await interaction.response.edit_message(
            view=ConfirmBuyButtons(
                bot=self._bot, pet_item=self._from_page[self.page - 1],
                interaction=interaction
            )
        )


class ConfirmBuyButtons(View):
    def __init__(
            self, pet_item: Pet, bot: ChisatoBot, interaction: MessageInteraction
    ):
        self.bot = bot
        self.pet_item = pet_item

        self._interaction = interaction
        self._end = False

        super().__init__(
            author=interaction.author, store=_t,
            interaction=self._interaction
        )

    async def on_timeout(self) -> None:
        if not self._end:
            for child in self.children:
                child.disabled = True

            try:
                await self._interaction.edit_original_response(view=self)
            except NotFound:
                pass
            except HTTPException:
                pass

    @ui.button(
        label="pets.purchase.confirm",
        emoji=SUCCESS_EMOJI, custom_id='pets_buy_confirm_button'
    )
    @check_in_fight_button
    @check_in_game_button
    async def buy_pet(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.databases.economy.remove_balance(
                guild=interaction.guild.id,
                member=interaction.author.id,
                amount=self.pet_item.cost
            )

            await self.bot.databases.pets.pet_add(
                guild=interaction.guild.id,
                member=interaction.author.id,
                pet_type=self.pet_item.name
            )

            await self.bot.databases.transactions.add(
                guild=interaction.guild.id,
                user=interaction.author.id,
                amount=self.pet_item.cost,
                locale_key="pets.purchase.transactions.buy_pet",
                typing=False
            )

            await interaction.edit_original_response(
                embed=EmbedUI(
                    title=_t.get("pets.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "pets.purchase.success", locale=interaction.guild_locale,
                        values=(
                            interaction.author.display_name,
                            _t.get(
                                "pets.dict.names", locale=interaction.guild_locale
                            )[self.pet_item.name],
                        )
                    ),
                    timestamp=interaction.created_at
                ),
                view=None
            )
        except NotEnoughMoney:
            await interaction.followup.send(
                embed=EmbedErrorUI(
                    description=_t.get("pets.error.buy.not_enough_money", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )
        except AlreadyHavePet:
            await self.bot.databases.economy.add_balance(
                guild=interaction.guild.id,
                member=interaction.author.id,
                amount=self.pet_item.cost
            )

            await interaction.followup.send(
                embed=EmbedErrorUI(
                    description=_t.get("pets.error.buy.already_has_pet", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )

    @ui.button(
        label="pets.back", emoji="<:ArrowLeft:1114648737730539620>",
        custom_id='pet_shop_back'
    )
    async def back_button(self, _, interaction: MessageInteraction) -> None:
        embeds, from_page = await PetShopPaginator.generate(bot=self.bot, locale=interaction.guild_locale)

        await interaction.response.edit_message(
            embed=embeds[0], view=PetShopPaginator(
                embeds=embeds, author=interaction.author,
                interaction=interaction, from_page=from_page
            )
        )

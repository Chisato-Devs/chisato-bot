import ast
import asyncio
from typing import TYPE_CHECKING, Union

from asyncpg import Record
from disnake import (
    ui,
    ApplicationCommandInteraction,
    HTTPException,
    NotFound,
    SelectOption,
    MessageInteraction,
    Forbidden
)

from utils.basic import View, EmbedUI, IntFormatter, EmbedErrorUI
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI, REGULAR_CURRENCY
from utils.exceptions import AlreadyHaveThisSubject, NotEnoughMoney, SubjectEnded
from utils.handlers.economy import check_in_game_button, check_in_fight_button
from utils.handlers.economy.views.pets import PetShopPaginator
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot
    from disnake.ext.commands import Bot

_t = ChisatoLocalStore.load("./cogs/economy/simple.py")


class ShopView(View):
    __slots__ = (
        "_author", "_interaction",
        "_bot", "_end"
    )

    def __init__(self, interaction: ApplicationCommandInteraction) -> None:
        self._author = interaction.author
        self._interaction = interaction

        self._bot: "ChisatoBot" = interaction.bot  # type: ignore
        self._end: bool = False

        super().__init__(
            author=self._author, timeout=300,
            store=_t, interaction=interaction
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

    class IncludePaginationMarryBanners(PaginatorView):
        __slots__ = (
            "_interaction", "_bot",
            "_end", "_from_page"
        )

        def __init__(self, **kwargs) -> None:
            self._interaction = kwargs.get("interaction")
            self._bot: "ChisatoBot" = self._interaction.bot
            self._end = False
            self._from_page = kwargs.pop("from_page")

            super().__init__(
                embeds=kwargs.pop("embeds"), author=self._interaction.author,
                footer=True, timeout=300, store=_t, interaction=self._interaction
            )

        async def before_edit_message(self, interaction: MessageInteraction) -> any:
            self._end = True

            if self._from_page[self.page] in (ast.literal_eval(
                    (await self._bot.databases.economy.get_marry_solo(interaction.guild, interaction.author))[7]
            )):
                self.button_disables(custom_ids=["buy_button"], disabled=True)
            else:
                self.button_disables(custom_ids=["buy_button"], disabled=False)

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

        @ui.button(emoji="<:Coins:1131412340752003173>", row=1, custom_id="buy_button")
        @check_in_fight_button
        @check_in_game_button
        async def buy_button(self, _, interaction: MessageInteraction) -> None:
            if not (
                    await self._bot.databases.economy.get_marry_solo(
                        interaction.guild, interaction.author
                    )
            ):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "loves.error.now_not_married", locale=interaction.guild_locale
                        ), member=interaction.author
                    ), ephemeral=True
                )

            try:
                coroutines = [
                    self._bot.databases.economy.remove_balance(
                        guild=interaction.guild.id, member=interaction.author.id, amount=2000
                    ),
                    self._bot.databases.economy.append_banner(
                        guild=interaction.guild, member=interaction.author, card_name=self._from_page[self.page]
                    ),
                    self._bot.databases.transactions.add(
                        guild=interaction.guild.id, user=interaction.author.id, amount=2000, typing=False,
                        locale_key="simple.shop.view.pagination.marry.banner.description.transaction"
                    )
                ]
                await asyncio.gather(*coroutines)
            except NotEnoughMoney:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "simple.shop.error.not_enough",
                            locale=interaction.guild_locale
                        ), member=interaction.author
                    ), ephemeral=True
                )
            except AlreadyHaveThisSubject:
                await self._bot.databases.economy.add_balance(
                    guild=interaction.guild.id, member=interaction.author.id, amount=2000
                )

                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "simple.shop.error.marries.already_have",
                            locale=interaction.guild_locale
                        ), member=interaction.author
                    ), ephemeral=True
                )
            else:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("simple.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "simple.shop.view.pagination.marry.banner.description",
                            locale=interaction.guild_locale, values=(
                                interaction.author.mention, interaction.author.name,
                                IntFormatter(2000).format_number()
                            )
                        )
                    ),
                    view=None
                )

    class IncludedPaginationLocal(PaginatorView):
        __slots__ = (
            "_interaction", "_bot",
            "_end", "_from_page"
        )

        def __init__(
                self,
                embeds: list[EmbedUI],
                interaction: MessageInteraction,
                from_page: dict[int, list[Record]]
        ) -> None:
            self._interaction = interaction
            self._bot: "ChisatoBot" = self._interaction.bot  # type: ignore
            self._end = False
            self._from_page = from_page
            self._get_from_id = {}

            super().__init__(
                embeds=embeds, author=self._interaction.author,
                footer=True, timeout=300, store=_t, interaction=self._interaction
            )
            self.set_options()

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

        def set_options(self) -> None:
            self._get_from_id.clear()
            options = []
            position_label = _t.get(
                "simple.shop.view.position",
                locale=self._interaction.guild_locale
            )

            for i, item in enumerate(self._from_page[self.page]):
                self._get_from_id[i] = item
                options.append(
                    SelectOption(
                        label=position_label + str(i + 1),
                        value=str(i)
                    )
                )

            self.get_item("local.buy_select").options = options

        async def before_edit_message(self, interaction: MessageInteraction) -> any:
            self._end = True
            self.set_options()

        @classmethod
        async def generate(
                cls, bot: Union["ChisatoBot", "Bot"],
                interaction: MessageInteraction | ApplicationCommandInteraction
        ) -> tuple[list[EmbedUI], dict[int, list[Record]]] | tuple[EmbedErrorUI, None]:
            author = interaction.author
            guild = interaction.guild

            items = [
                item for item in await bot.databases.economy.get_shop_items(guild=guild)
                if guild.get_role(item[1])
            ]
            if not items:
                return EmbedErrorUI(
                    description=_t.get(
                        "simple.shop.view.error.not_found_in_local",
                        locale=interaction.guild_locale
                    ),
                    member=author
                ), None

            embeds = []
            text = ''
            from_page = {}
            _ni = []

            desc = _t.get(
                "simple.shop.view.pagination.generator",
                locale=interaction.guild_locale
            )

            unlimited = _t.get(
                "simple.shop.view.pagination.unlimited",
                locale=interaction.guild_locale
            )

            title = _t.get("simple.shop.local.title", locale=interaction.guild_locale)

            page = 1
            for i, item in enumerate(items, start=1):
                role = guild.get_role(item[1])
                _ni.append(item)

                text += desc.format(
                    str(i), role.mention, role.name, IntFormatter(item[5]).format_number(),
                    REGULAR_CURRENCY, item[5], item[2] if not item[3] else unlimited,
                    item[4] if item[4] else '-'
                )

                if i % 5 == 0 or i == len(items):
                    from_page[page] = _ni.copy()
                    embeds.append(EmbedUI(title=title, description=text))

                    text = ''
                    _ni.clear()
                    page += 1

            return embeds, from_page

        @staticmethod
        async def create(interaction: MessageInteraction) -> None:
            embeds, from_page = await ShopView.IncludedPaginationLocal.generate(
                bot=interaction.bot,
                interaction=interaction
            )
            if isinstance(embeds, EmbedErrorUI):
                return await interaction.response.send_message(
                    embed=embeds, ephemeral=True
                )

            await interaction.response.edit_message(
                embed=embeds[0], view=ShopView.IncludedPaginationLocal(
                    interaction=interaction, from_page=from_page,
                    embeds=embeds
                )
            )

        class IncludeConfirm(View):
            def __init__(
                    self, bot: "ChisatoBot",
                    interaction: MessageInteraction,
                    role_item: Record
            ) -> None:
                self._end = False
                self._interaction = interaction
                self._bot = bot
                self._item = role_item

                super().__init__(
                    store=_t, interaction=interaction,
                    author=interaction.author,
                    timeout=300
                )

            async def on_timeout(self) -> None:
                if not self._end:
                    for i in self.children:
                        i.disabled = True

                    try:
                        await self._interaction.edit_original_response(view=self)
                    except NotFound:
                        pass
                    except HTTPException:
                        pass

            @ui.button(
                label="simple.shop.local.select.confirm.button.label",
                emoji=SUCCESS_EMOJI, custom_id='pets_buy_confirm_button'
            )
            async def confirm(self, _, interaction: MessageInteraction) -> None:
                self._end = True

                if not (role := interaction.guild.get_role(self._item[1])):
                    await self._bot.databases.economy.remove_item(
                        guild=interaction.guild, role=self._item[1]
                    )
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.local.error.role_removed",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        )
                    )

                try:
                    if role in interaction.author.roles:
                        raise AlreadyHaveThisSubject

                    await self._bot.databases.economy.remove_balance(
                        guild=interaction.guild.id,
                        member=interaction.author.id,
                        amount=self._item[5]
                    )

                    await self._bot.databases.economy.remove_count(
                        guild=interaction.guild, role=self._item[1]
                    )

                    await interaction.author.add_roles(role)

                    await self._bot.databases.transactions.add(
                        guild=interaction.guild.id, user=interaction.author.id, amount=self._item[5],
                        locale_key="simple.shop.local.role_bought.transaction", typing=False
                    )
                except NotEnoughMoney:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.local.error.not_enough",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ), ephemeral=True
                    )
                except Forbidden:
                    await self._bot.databases.economy.add_count(
                        guild=interaction.guild,
                        role=self._item[1]
                    )

                    await self._bot.databases.economy.add_balance(
                        guild=interaction.guild.id,
                        member=interaction.author.id,
                        amount=self._item[5]
                    )

                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.local.error.forbidden",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ), ephemeral=True
                    )
                except SubjectEnded:
                    await self._bot.databases.economy.add_balance(
                        guild=interaction.guild.id,
                        member=interaction.author.id,
                        amount=self._item[5]
                    )

                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.local.error.subject_ended",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ), ephemeral=True
                    )
                except AlreadyHaveThisSubject:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.local.error.already_had",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ), ephemeral=True
                    )
                else:
                    await interaction.response.edit_message(
                        embed=EmbedUI(
                            title=_t.get("simple.success.title", locale=interaction.guild_locale),
                            description=_t.get(
                                "simple.shop.local.button.callback.description",
                                locale=interaction.guild_locale,
                                values=(
                                    interaction.author.mention, interaction.author.name,
                                    IntFormatter(self._item[5]).format_number(), self._item[5],
                                    role.mention, role.name
                                )
                            )
                        ),
                        view=None
                    )

            @ui.button(
                label="simple.shop.local.select.confirm.button.label.back",
                custom_id="local.shop.back_button",
                emoji="<:ArrowLeft:1114648737730539620>"
            )
            async def back(self, _, interaction: MessageInteraction) -> None:
                self._end = True
                await ShopView.IncludedPaginationLocal.create(interaction)

        @ui.select(
            placeholder="simple.shop.local.select.placeholder",
            options=[
                SelectOption(
                    label="Сдохло"
                )
            ],
            custom_id="local.buy_select"
        )
        @check_in_fight_button
        @check_in_game_button
        async def buy_select(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
            self._end = True
            item = self._get_from_id[int(select.values[0])]
            role = interaction.guild.get_role(item[1])
            if not role:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "simple.shop.local.error.role_removed",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    )
                )

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("simple.shop.local.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "simple.shop.view.pagination.generator",
                        locale=interaction.guild_locale,
                        values=(
                            str(int(select.values[0]) + 1), role.mention, role.name,
                            IntFormatter(item[5]).format_number(), REGULAR_CURRENCY,
                            item[5], item[2] if not item[3] else _t.get(
                                "simple.shop.view.pagination.unlimited",
                                locale=interaction.guild_locale
                            ),
                            item[4] if item[4] else '-'
                        )
                    )
                ),
                view=self.IncludeConfirm(
                    bot=self._bot, interaction=interaction,
                    role_item=item
                )
            )

    @ui.string_select(
        placeholder="simple.shop.local.select.select_shop.placeholder",
        custom_id="shop_select_menu", options=[
            SelectOption(
                label="simple.shop.local.option.label",
                description="simple.shop.local.option.description",
                value="local", emoji="<:shop_local:1185656146778923100>"
            ),
            SelectOption(
                label="simple.shop.loves.option.label",
                description="simple.shop.loves.option.description",
                value="love", emoji="<:Heart:1131438234296123513>"
            ),
            SelectOption(
                label="simple.shop.pets.option.label",
                description="simple.shop.pets.option.description",
                value="pets", emoji="<:pet:1185655303174365304>"
            )
        ]
    )
    async def select_shop(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self._end = True
        match select.values[0]:
            case "local":
                await self.IncludedPaginationLocal.create(interaction)
            case "love":
                if not (
                        marry_data := await self._bot.databases.economy.get_marry_solo(
                            interaction.guild, interaction.author
                        )
                ):
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "simple.shop.error.not_married",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ), ephemeral=True
                    )

                from_name = {
                    "love2": "https://i.ibb.co/TL7Z11X/love2.png",
                    "love3": "https://i.ibb.co/42nN9y2/love3.png",
                    "love4": "https://i.ibb.co/3dy2vns/love4.png"
                }

                data_list = ast.literal_eval(marry_data[7])

                from_page = {}
                embeds = []
                description = _t.get(
                    "simple.shop.loves.description",
                    locale=interaction.guild_locale
                )

                for i, data in enumerate(from_name.items()):
                    from_page[i + 1] = data[0]
                    embeds.append(
                        EmbedUI(
                            title=_t.get("simple.shop.loves.title", locale=interaction.guild_locale),
                            description=description.format(
                                IntFormatter(2000).format_number(),
                                SUCCESS_EMOJI if data[0] in data_list else ERROR_EMOJI,
                                _t.get(
                                    "simple.shop.bought" if data[0] in data_list else "simple.shop.not_bought",
                                    locale=interaction.guild_locale
                                )
                            )
                        ).set_image(data[1])
                    )

                view_obj = self.IncludePaginationMarryBanners(
                    interaction=interaction, from_page=from_page, embeds=embeds
                )
                await view_obj.before_edit_message(interaction)

                await interaction.response.edit_message(
                    embed=embeds[0], view=view_obj
                )
            case "pets":
                embeds, from_page = await PetShopPaginator.generate(bot=self._bot, locale=interaction.guild_locale)

                await interaction.response.edit_message(
                    embed=embeds[0], view=PetShopPaginator(
                        embeds=embeds, author=interaction.author,
                        interaction=interaction, from_page=from_page
                    )
                )

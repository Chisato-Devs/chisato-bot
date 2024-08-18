from typing import Self, Union

from disnake import MessageInteraction, ApplicationCommandInteraction, Member, SelectOption, ui, NotFound, \
    HTTPException, ModalInteraction, Role

from utils.basic import View, EmbedUI, EmbedErrorUI
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI, REGULAR_CURRENCY
from utils.exceptions import AlreadyInShop, MaxShopItems
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton, EndView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class EconomyModule(View, SettingModule):
    __slots__ = (
        "bot",
        "option",
        "__end",
        "member",
        "status",
        "__interaction"
    )

    def __init__(
            self,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            member: Member
    ) -> None:
        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
        self.option: SelectOption | None = None
        self.member = member
        self.status: bool = False

        self.__end = False
        self.__interaction = interaction

        super().__init__(
            store=_t, interaction=interaction,
            author=interaction.author
        )

        self.add_item(BackButton(self.bot, row=2, module=self))

    @property
    def end(self) -> bool:
        return self.__end

    @end.setter
    def end(self, value: bool) -> None:
        self.__end = value

    async def on_timeout(self) -> None:
        if not self.__end:
            for i in self.children:
                i.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except NotFound:
                pass
            except HTTPException:
                pass

    async def main_callback(self, interaction: MessageInteraction) -> None:
        await interaction.response.edit_message(
            view=self, embed=EmbedUI(
                title=_t.get(
                    "settings.economy.title",
                    locale=interaction.guild_locale,
                    values=(REGULAR_CURRENCY,)
                ),
                description=_t.get(
                    "settings.economy.description",
                    locale=interaction.guild_locale
                )
            )
        )

    def set_items(self) -> None:
        label = "settings.economy.disable" if self.status else "settings.economy.enable"
        self.switch_economy.label = _t.get(
            label, locale=self.__interaction.guild_locale
        )

        self.switch_economy.emoji = SUCCESS_EMOJI if self.status else ERROR_EMOJI

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.settings.get(guild=self.__interaction.guild.id)
        self.status = True if data_obj and data_obj[2] else False

        option_label = "settings.economy.option.disable" if self.status else "settings.economy.option.enable"
        self.option = SelectOption(
            label=_t.get(option_label, locale=self.__interaction.guild_locale),
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI,
            value=self.__class__.__name__
        )

        self.set_items()
        return self

    @ui.button(label="Сдохло", emoji=SUCCESS_EMOJI, custom_id="economy.switch.button")
    async def switch_economy(self, _, interaction: MessageInteraction) -> None:
        await self.bot.databases.settings.switch(guild=interaction.guild.id, economy=True)
        await self.initialize_database()

        await interaction.response.edit_message(view=self)

    class IncludeView(View):
        __slots__ = (
            "bot", "__interaction"
        )

        def __init__(
                self,
                interaction: MessageInteraction | ApplicationCommandInteraction,
                main_interaction: MessageInteraction | ApplicationCommandInteraction
        ) -> None:
            self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
            self.__main_interaction = main_interaction
            self.__interaction = interaction
            self.__end = False

            super().__init__(
                store=_t, interaction=interaction,
                author=interaction.author, timeout=300
            )

        async def on_timeout(self) -> None:
            if not self.__end:
                for i in self.children:
                    i.disabled = True

                try:
                    await self.__interaction.edit_original_response(view=self)
                except NotFound:
                    pass
                except HTTPException:
                    pass

        async def set_options(self) -> "EconomyModule.IncludeView":
            options = []
            for i in await self.bot.databases.economy.get_shop_items(
                    guild=self.__interaction.guild
            ):
                if role := self.__interaction.guild.get_role(i[1]):
                    options.append(
                        SelectOption(
                            label=f"{role.emoji if role.emoji else ''}{role.name}",
                            value=str(i[1])
                        )
                    )
                    continue
                options.append(
                    SelectOption(
                        label=str(i[1]), value=str(i[1])
                    )
                )

            if options:
                self.remove_shop_role_select.options = options
            else:
                self.remove_item(self.remove_shop_role_select)

            return self

        class IncludeModal(ui.Modal):
            __slots__ = (
                "_bot", "_role",
                "_main_interaction"
            )

            def __init__(
                    self, main_interaction: MessageInteraction,
                    role: Role
            ) -> None:
                self._bot: Union["ChisatoBot", "Bot"] = main_interaction.bot
                self._role = role
                self._main_interaction = main_interaction

                super().__init__(
                    title=_t.get(
                        "settings.economy.local.modal.title",
                        locale=self._main_interaction.guild_locale
                    ),
                    custom_id="shop.setting.role_select.modal",
                    components=[
                        ui.TextInput(
                            label=_t.get(
                                "settings.economy.local.modal.option.count.label",
                                locale=self._main_interaction.guild_locale
                            ),
                            placeholder=_t.get(
                                "settings.economy.local.modal.option.count.placeholder",
                                locale=self._main_interaction.guild_locale
                            ),
                            custom_id="count", required=False,
                            min_length=1, max_length=8,
                        ),
                        ui.TextInput(
                            label=_t.get(
                                "settings.economy.local.modal.option.cost.label",
                                locale=self._main_interaction.guild_locale
                            ),
                            placeholder="10000",
                            min_length=1, max_length=8,
                            custom_id="cost"
                        ),
                        ui.TextInput(
                            label=_t.get(
                                "settings.economy.local.modal.option.desc.label",
                                locale=self._main_interaction.guild_locale
                            ),
                            placeholder=_t.get(
                                "settings.economy.local.modal.option.desc.description",
                                locale=self._main_interaction.guild_locale
                            ),
                            min_length=1, max_length=255,
                            custom_id="description",
                            required=False
                        )
                    ]
                )

            async def callback(self, interaction: ModalInteraction, /) -> None:
                count = interaction.text_values["count"]
                cost = interaction.text_values["cost"]
                description = interaction.text_values["description"]

                if count:
                    try:
                        count = int(count)
                    except ValueError:
                        return await interaction.response.send_message(
                            embed=EmbedErrorUI(
                                description=_t.get(
                                    "settings.economy.local.modal.error.invalid_count",
                                    locale=interaction.guild_locale
                                ),
                                member=interaction.author
                            ),
                            ephemeral=True
                        )
                else:
                    count = True

                try:
                    cost = int(cost)
                except ValueError:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "settings.economy.local.modal.error.invalid_cost",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                try:
                    await self._bot.databases.economy.add_item(
                        guild=interaction.guild, role=self._role,
                        count=count, cost=cost, description=description
                    )
                except AlreadyInShop:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "settings.economy.local.modal.error.in_shop",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )
                except MaxShopItems:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "settings.economy.local.modal.error.max_roles",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                if not interaction.guild.get_role(self._role.id):
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "settings.economy.local.modal.error.role_removed",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get(
                            "settings.success.title",
                            locale=interaction.guild_locale
                        ),
                        description=_t.get(
                            "settings.economy.local.modal.callback.success",
                            locale=interaction.guild_locale
                        )
                    )
                )

                try:
                    await self._main_interaction.edit_original_response(
                        embed=EmbedUI(
                            title=_t.get(
                                "settings.success.title",
                                locale=interaction.guild_locale
                            ),
                            description=_t.get(
                                "settings.economy.local.modal.callback.success.main",
                                locale=interaction.guild_locale,
                                values=(
                                    interaction.author.mention, interaction.author.name,
                                    self._role.mention, self._role.name
                                )
                            )
                        )
                    )
                except NotFound:
                    pass
                except HTTPException:
                    pass

        @ui.role_select(
            placeholder="settings.economy.role_select.placeholder",
            custom_id="shop.setting.role_select"
        )
        async def shop_role_select(
                self, select: ui.RoleSelect,
                interaction: MessageInteraction
        ) -> None:
            self.__end = True
            await interaction.response.send_modal(
                self.IncludeModal(
                    main_interaction=self.__main_interaction,
                    role=select.values[0]
                )
            )

        @ui.string_select(
            placeholder="settings.economy.select.placeholder",
            custom_id="shop.setting.remove.role_select",
            options=[SelectOption(label="Сдохло", value="Да")],
            min_values=1, max_values=1
        )
        async def remove_shop_role_select(
                self, select: ui.StringSelect,
                interaction: MessageInteraction
        ) -> None:
            self.__end = True
            role = select.values

            await self.bot.databases.economy.remove_item(
                guild=interaction.guild, role=int(role[0])
            )

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get(
                        "settings.success.title",
                        locale=interaction.guild_locale
                    ),
                    description=_t.get(
                        "settings.economy.select.callback.description",
                        locale=interaction.guild_locale

                    )
                ),
                view=None
            )

            try:
                await self.__main_interaction.edit_original_response(
                    embed=EmbedUI(
                        title=_t.get(
                            "settings.success.title",
                            locale=interaction.guild_locale
                        ),
                        description=_t.get(
                            "settings.economy.select.callback.main.description",
                            locale=interaction.guild_locale,
                            values=(interaction.author.mention, interaction.author.name, role[0])
                        )
                    ),
                    view=EndView(
                        author=interaction.author,
                        interaction=self.__main_interaction
                    )
                )
            except NotFound:
                pass
            except HTTPException:
                pass

    @ui.button(
        label="settings.economy.button.setting.label",
        emoji="<:shop_local:1185656146778923100>",
        custom_id="economy.setting.shop"
    )
    async def setting_shop(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("settings.economy.local.title", locale=interaction.guild_locale),
                description=_t.get("settings.economy.local.description", locale=interaction.guild_locale)
            ),
            ephemeral=True,
            view=await self.IncludeView(
                interaction=interaction, main_interaction=self.__interaction
            ).set_options()
        )

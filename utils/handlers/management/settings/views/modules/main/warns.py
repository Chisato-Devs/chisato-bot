from datetime import datetime
from typing import Self

from disnake import MessageInteraction, ApplicationCommandInteraction, Member, SelectOption, errors, ui, \
    ModalInteraction, HTTPException

from utils.basic import View, EmbedUI, EmbedErrorUI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton, EndView
from utils.handlers.moderation import time_converter
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class WarnsModule(View, SettingModule):
    __slots__ = (
        "status",
        "bot",
        "option",
        "__end",
        "__interaction"
    )

    main_module = True

    def __init__(
            self,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            member: Member
    ) -> None:
        self.status = False
        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
        self.option: SelectOption | None = None

        self.__end = False
        self.__interaction: MessageInteraction | ApplicationCommandInteraction = interaction

        super().__init__(
            author=member, timeout=300,
            store=_t, interaction=interaction
        )

        self.add_item(BackButton(self.bot, row=1, module=self))

    @property
    def end(self) -> bool:
        return self.__end

    @end.setter
    def end(self, value: bool) -> None:
        self.__end = value

    async def main_callback(self, interaction: MessageInteraction) -> None:
        await self.initialize_database()
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("settings.warns.title", locale=interaction.guild_locale),
                description=_t.get("settings.warns.description", locale=interaction.guild_locale)
            ), view=self
        )

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except errors.InteractionResponded:
                return None
            except errors.HTTPException:
                return None

    async def initialize_database(self) -> Self:
        self.option = SelectOption(
            label=_t.get(
                "settings.warns.option.label",
                locale=self.__interaction.guild_locale
            ),
            emoji="<:ProtectionOFF:1114647772440821954>",
            value=type(self).__name__
        )

        return self

    @ui.button(
        label="settings.warns.button.change.label",
        emoji='<:Edit:1116358712794296460>',
        custom_id='edit_punishment/time/count'
    )
    async def edit_settings(self, _: ui.Button, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("settings.next_set.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.warns.button.callback.description",
                    locale=interaction.guild_locale
                )
            ), view=self.IncludeSelect(
                author=interaction.author, interaction=self.__interaction
            ),
            ephemeral=True
        )

    class IncludeSelect(View):
        __slots__ = (
            '_author', '_interaction', '__end'
        )

        def __init__(
                self, author: Member, interaction: MessageInteraction
        ) -> None:
            self._author = author
            self._interaction = interaction

            self.__end = False

            super().__init__(
                author=author, timeout=300,
                interaction=interaction, store=_t
            )

        async def on_timeout(self) -> None:
            if not self.__end:
                for child in self.children:
                    child.disabled = True

                try:
                    await self._interaction.edit_original_response(view=self)
                except errors.InteractionResponded:
                    return None
                except errors.HTTPException:
                    return None

        class IncludeSelectFromSelect(View):
            __slots__ = (
                '_author', '_interaction', 'end', '_main'
            )

            def __init__(
                    self, author: Member, interaction: MessageInteraction, main_interaction: MessageInteraction
            ) -> None:
                self._author = author
                self._interaction = interaction
                self._main = main_interaction

                self.end = False

                super().__init__(
                    author=author, timeout=300,
                    store=_t, interaction=interaction
                )

                self.add_item(self.SelectMenuPunishment(last=self, interaction=self._main))

            async def on_timeout(self) -> None:
                if not self.end:
                    for child in self.children:
                        child.disabled = True

                    try:
                        await self._interaction.edit_original_response(view=self)
                    except errors.InteractionResponded:
                        return None
                    except errors.HTTPException:
                        return None

            class SelectMenuPunishment(ui.StringSelect):
                __slots__ = (
                    '_last', '_bot', '_interaction'
                )

                def __init__(self, last: View, interaction: MessageInteraction) -> None:
                    self._last = last
                    self._bot: 'ChisatoBot' = interaction.bot  # type: ignore
                    self._interaction = interaction

                    super().__init__(
                        placeholder="settings.warns.punishment_select.placeholder", options=[
                            SelectOption(
                                label="settings.warns.punishment_select.option.kick",
                                value="kick_value",
                                description="settings.warns.punishment_select.option.kick.description",
                                emoji="<:removeuser:1114369700554621010>"
                            ),
                            SelectOption(
                                label="settings.warns.punishment_select.option.timeout",
                                value="timeout_value",
                                description="settings.warns.punishment_select.option.timeout.description",
                                emoji="<:mute:1114367698479095889>"
                            ),
                            SelectOption(
                                label="settings.warns.punishment_select.option.ban",
                                value="ban_value",
                                description="settings.warns.punishment_select.option.ban.description",
                                emoji="<:axe:1114245100852236399>"
                            )
                        ]
                    )

                async def callback(self, interaction: MessageInteraction, /) -> None:
                    self._last.end = True
                    punishment_type_formatted: str = self.values[0][:-6]

                    await self._bot.databases.moderation.add_global_warns_settings(
                        guild=interaction.guild,
                        punishment_type=punishment_type_formatted
                    )

                    await interaction.response.edit_message(embed=EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.warns.punishment_select.success",
                            locale=interaction.guild_locale
                        )
                    ), view=None)

                    try:
                        await self._interaction.edit_original_response(
                            embed=EmbedUI(
                                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                                description=_t.get(
                                    "settings.warns.punishment_select.success.old",
                                    locale=interaction.guild_locale,
                                    values=(punishment_type_formatted,)
                                )
                            ),
                            view=EndView(
                                author=interaction.author, interaction=interaction
                            )
                        )
                    except HTTPException:
                        pass

        @ui.string_select(
            placeholder="settings.warns.select.placeholder", options=[
                SelectOption(
                    label="settings.warns.select.option.punishment",
                    emoji='<:hammer:1131515651626897428>', value="punishment"
                ),
                SelectOption(
                    label="settings.warns.select.option.time",
                    emoji='<:KristaHave7mopsin:1113824549310578699>', value="time"
                ),
                SelectOption(
                    label="settings.warns.select.option.max_count",
                    emoji='<:Star2:1131445020210245715>', value="count"
                )
            ]
        )
        async def select_callback(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
            self.__end = True
            match select.values[0]:
                case 'punishment':
                    await interaction.response.edit_message(
                        embed=EmbedUI(
                            title=_t.get("settings.next_set.title", locale=interaction.guild_locale),
                            description=_t.get(
                                "settings.warns.select.punishment.description",
                                locale=interaction.guild_locale
                            )
                        ),
                        view=self.IncludeSelectFromSelect(
                            author=interaction.author, interaction=interaction, main_interaction=self._interaction
                        )
                    )
                case 'time':
                    await interaction.response.send_modal(
                        WarnsModule.IncludeModal(
                            modal_type=select.values[0],
                            main_interaction=self._interaction
                        )
                    )
                case 'count':
                    await interaction.response.send_modal(
                        WarnsModule.IncludeModal(
                            modal_type=select.values[0],
                            main_interaction=self._interaction
                        )
                    )

    class IncludeModal(ui.Modal):
        __slots__ = (
            '_main_interaction', '_bot',
            'og_embed', 'modal_type'
        )

        def __init__(self, modal_type: str, main_interaction: MessageInteraction) -> None:
            self._main_interaction = main_interaction
            self._bot: 'ChisatoBot' = main_interaction.bot  # type: ignore
            self.modal_type = modal_type

            title = 'Пишите в тп модалка сдохла'
            components = [
                ui.TextInput(
                    label='Пишите в тп',
                    custom_id='__error__'
                )
            ]

            match modal_type:
                case 'time':
                    title = _t.get(
                        "settings.warns.modal.time.title",
                        locale=main_interaction.guild_locale
                    )
                    components = [
                        ui.TextInput(
                            label=_t.get(
                                "settings.warns.modal.component.time.label",
                                locale=main_interaction.guild_locale
                            ),
                            placeholder='1m | 2h | 3d',
                            custom_id=modal_type,
                            max_length=50
                        )
                    ]
                case 'count':
                    title = _t.get(
                        "settings.warns.modal.count.title",
                        locale=main_interaction.guild_locale
                    )
                    components = [
                        ui.TextInput(
                            label=_t.get(
                                "settings.warns.modal.component.count.label",
                                locale=main_interaction.guild_locale
                            ),
                            placeholder="98",
                            custom_id=modal_type,
                            max_length=2
                        )
                    ]

            super().__init__(title=title, components=components, custom_id='modal__warns_module_stg')

            self.og_embed: EmbedUI = EmbedUI(
                title=_t.get("settings.success.title", locale=main_interaction.guild_locale),
                description=_t.get(
                    "settings.warns.modal.og_embed.description", locale=main_interaction.guild_locale
                )
            )

        async def callback(self, interaction: ModalInteraction, /) -> None:
            async def create_embed(description: str) -> None:
                await interaction.response.edit_message(embed=self.og_embed, view=None)
                try:
                    await self._main_interaction.edit_original_response(embed=EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=description
                    ), view=EndView(
                        author=interaction.author, interaction=interaction
                    ))
                except HTTPException:
                    pass

            match self.modal_type:
                case 'time':
                    if (_data := await self._bot.databases.moderation.get_global_warns_settings(
                            guild=interaction.guild
                    ))[1] != 'timeout' and _data != 'ban':
                        return await interaction.response.edit_message(
                            embed=EmbedErrorUI(
                                _t.get(
                                    "settings.warns.modal.error.punishment.time", locale=interaction.guild_locale
                                ), interaction.author
                            ),
                            view=None
                        )

                    inputted_punishment_time: str = interaction.text_values[self.modal_type]

                    result: datetime | EmbedErrorUI = await time_converter(
                        inputted_punishment_time,
                        interaction.author,
                        self.modal_type == "timeout",
                        interaction.guild_locale
                    )

                    if isinstance(result, datetime):
                        await self._bot.databases.moderation.add_global_warns_settings(
                            guild=interaction.guild,
                            punishment_time=inputted_punishment_time
                        )

                        await create_embed(
                            _t.get(
                                "settings.warns.modal.success.time.description",
                                locale=interaction.guild_locale,
                                values=(inputted_punishment_time,)
                            )
                        )
                    else:
                        await interaction.response.edit_message(embed=result, view=None)
                case 'count':
                    warnings_limit: str = interaction.text_values[self.modal_type]

                    if warnings_limit.isdigit():
                        warnings_limit: int = int(warnings_limit)

                        if warnings_limit > 10:
                            embed: EmbedErrorUI = EmbedErrorUI(
                                "кол-во предупреждений не может быть больше 10!", interaction.author
                            )
                            return await interaction.response.edit_message(embed=embed, view=None)

                        await self._bot.databases.moderation.add_global_warns_settings(
                            guild=interaction.guild,
                            warnings_limit=warnings_limit
                        )

                        await create_embed(
                            _t.get(
                                "settings.warns.modal.success.limit.description",
                                locale=interaction.guild_locale,
                                values=(warnings_limit,)
                            )
                        )
                    else:
                        embed: EmbedErrorUI = EmbedErrorUI(
                            _t.get("settings.warns.modal.error.data_type", locale=interaction.guild_locale),
                            interaction.author
                        )
                        await interaction.response.edit_message(embed=embed, view=None)

from json import loads
from json.decoder import JSONDecodeError
from typing import Self, TYPE_CHECKING

from disnake import MessageInteraction, ApplicationCommandInteraction, Member, SelectOption, errors, ui, Message, \
    TextInputStyle, ModalInteraction

from utils.basic import View, EmbedUI, EmbedErrorUI
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton, EndView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")

if TYPE_CHECKING:
    from utils.basic import ChisatoBot


class LevelsModule(View, SettingModule):
    __slots__ = (
        "status",
        "__end",
        "alert_status",
        "bot",
        "option",
        "__interaction"
    )

    def __init__(
            self,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            member: Member
    ) -> None:
        self.status = False
        self.alert_status = False
        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
        self.option: SelectOption | None = None

        self.__end = False
        self.__interaction: MessageInteraction | ApplicationCommandInteraction = interaction

        super().__init__(
            author=member, timeout=300, store=_t,
            interaction=self.__interaction
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
                title=_t.get("settings.level.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.level.embed.description", locale=interaction.guild_locale
                )
            ),
            view=self
        )

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except errors.InteractionResponded:
                pass
            except errors.HTTPException:
                pass
            finally:
                return None

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.level.settings_values(guild=self.__interaction.guild.id)
        self.alert_status = True if data_obj and data_obj[1] else False
        self.status = True if data_obj and data_obj[2] else False

        self.set_buttons()

        option_label = "settings.level.option.disable" if self.status else "settings.level.option.enable"
        self.option = SelectOption(
            label=_t.get(option_label, locale=self.__interaction.guild_locale),
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI,
            value=self.__class__.__name__
        )

        return self

    def set_buttons(self) -> None:
        self.switch_level_status.label = _t.get(
            "settings.level.button.switch.disable", locale=self.__interaction.guild_locale
        ) if self.status else _t.get(
            "settings.level.button.switch.enable", locale=self.__interaction.guild_locale
        )
        self.switch_level_status.emoji = SUCCESS_EMOJI if self.status else ERROR_EMOJI

        self.switch_alert_status.label = _t.get(
            "settings.level.button.alert.disable", locale=self.__interaction.guild_locale
        ) if self.alert_status else _t.get(
            "settings.level.button.alert.enable", locale=self.__interaction.guild_locale
        )
        self.switch_alert_status.emoji = SUCCESS_EMOJI if self.alert_status else ERROR_EMOJI

    @ui.button(label="Чета сдохло", custom_id="switch_level_status", row=0)
    async def switch_level_status(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        await self.bot.databases.level.settings_status_switch(guild=interaction.guild.id)
        await self.initialize_database()
        await interaction.response.edit_message(view=self)

    @ui.button(label="Чета сдохло x2", custom_id="switch_alert_status", row=0)
    async def switch_alert_status(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        await self.bot.databases.level.settings_status_switch(guild=interaction.guild.id, alert=True)
        await self.initialize_database()
        await interaction.response.edit_message(view=self)

    class IncludeModal(ui.Modal):
        def __init__(
                self, interaction: MessageInteraction, *, last_message: Message,
                bot: 'ChisatoBot', view_obj: "LevelsModule.IncludeButtons"
        ) -> None:
            self.bot = bot

            self.__last = last_message
            self.__interaction = interaction
            self.__view_obj = view_obj

            super().__init__(
                title=_t.get(
                    "settings.level.modal.title", locale=interaction.guild_locale,
                    values=(
                        interaction.author.global_name[:10]
                    )
                ),
                custom_id="LevelsIncludeModalResponse",
                components=[
                    ui.TextInput(
                        label=_t.get(
                            "settings.level.modal.component.json.label",
                            locale=interaction.guild_locale
                        ),
                        custom_id="JsonResponseFromUser",
                        max_length=4000,
                        style=TextInputStyle.paragraph
                    )
                ]
            )

        async def callback(self, interaction: ModalInteraction) -> None:
            data = interaction.text_values["JsonResponseFromUser"]
            try:
                inputted_text_dict = loads(data)
            except (TypeError, JSONDecodeError):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "settings.level.modal.callback.error.json",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

            if (
                    not inputted_text_dict["embeds"] or
                    (
                            not isinstance(inputted_text_dict, dict)
                            or len(inputted_text_dict["embeds"]) > 3
                    )
            ):
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "settings.level.modal.callback.error.more3",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

            attrs = {
                "member": str(interaction.author),
                "last_rank": str(9),
                "rank": str(10),
                "now_exp": str(0),
                "need_exp": str(300),
                "prestige": str(5),
                "can_prestige": _t.get(
                    "settings.level.modal.callback.preview.can_prestige",
                    locale=interaction.guild_locale
                ),
                "member_avatar": interaction.author.display_avatar.url[8:],
            }
            try:
                embeds = [
                             EmbedUI(
                                 title=_t.get("settings.success.title", locale=interaction.guild_locale),
                                 description=_t.get(
                                     "settings.level.modal.callback.success.changed",
                                     locale=interaction.guild_locale,
                                     values=(interaction.author.mention, interaction.author.name)
                                 ),
                                 timestamp=interaction.created_at
                             ),
                             EmbedUI(
                                 title=_t.get(
                                     "settings.level.modal.callback.preview.embeds",
                                     locale=interaction.guild_locale
                                 )
                             )
                         ] + [
                             EmbedUI.from_dict_with_attrs(embed_data, attrs)
                             for embed_data in inputted_text_dict["embeds"]
                         ]
            except Exception as e:
                _ = e
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        _t.get(
                            "settings.level.modal.callback.error.idk",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ), ephemeral=True
                )

            try:
                await self.__last.edit(
                    embeds=embeds, view=EndView(
                        author=interaction.author, interaction=self.__interaction
                    )
                )

            except (errors.Forbidden or errors.HTTPException):
                return await interaction.response.edit_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "settings.level.modal.callback.error.message_removed",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    view=None
                )

            try:
                await self.bot.databases.level.set_embed_data(
                    guild=interaction.guild.id, embed_data=str(inputted_text_dict["embeds"])
                )
                embed = EmbedUI(
                    title=_t.get("settings.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "settings.level.modal.callback.preview.initialized",
                        locale=interaction.guild_locale
                    ),
                    timestamp=interaction.created_at
                )

                await interaction.response.edit_message(embed=embed, view=None)
            except (errors.HTTPException or errors.Forbidden):
                pass

    class IncludeButtons(View):
        def __init__(self, interaction: MessageInteraction, last_message: Message) -> None:
            self.__interaction = interaction
            self.__last = last_message
            self.__end = False

            self.bot: 'ChisatoBot' = interaction.bot  # type: ignore

            super().__init__(
                author=interaction.author, timeout=300,
                store=_t, interaction=interaction
            )

            self.add_item(
                ui.Button(
                    label="settings.level.buttons.link_button.json_constructor",
                    url="https://discohook.org", emoji="<:Link:1142817574644633742>"
                )
            )

        async def on_timeout(self, not_check: bool = False) -> None:
            if not self.__end or not_check:
                for child in self.children:
                    child.disabled = True
                try:
                    await self.__interaction.edit_original_response(view=self)
                except (errors.Forbidden or errors.HTTPException or errors.InteractionResponded):
                    pass

        @ui.button(
            label="settings.button.continue.label",
            emoji="<:Arrowright:1114674030331576401>",
            custom_id="LevelsNextSet"
        )
        async def next_set(self, _, interaction: MessageInteraction) -> None:
            self.__end = True

            await interaction.response.send_modal(
                LevelsModule.IncludeModal(interaction, bot=self.bot, last_message=self.__last, view_obj=self)
            )

        @ui.button(
            label="settings.button.refresh.label",
            emoji="<:Refresh3:1114986806480478318>",
            custom_id="refresh_embed_levels"
        )
        async def refresh_embed(self, _, interaction: MessageInteraction) -> None:
            self.__end = True

            embed = EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.level.buttons.button.refresh.success",
                    locale=interaction.guild_locale
                ),
                timestamp=interaction.created_at
            )
            try:
                await interaction.response.defer()
                await interaction.followup.delete_message(interaction.message.id)
            except errors.Forbidden:
                pass

            await self.bot.databases.level.set_embed_data(guild=interaction.guild.id)

            try:
                await self.__last.edit(
                    embed=embed, view=EndView(
                        author=interaction.author, interaction=self.__interaction
                    )
                )

            except (errors.Forbidden or errors.HTTPException):
                pass

    @ui.button(
        label="settings.level.buttons.button.setting_alerts.label",
        emoji="<:Messagebox:1131481077052080149>", row=1
    )
    async def setting_level(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        embed = EmbedUI(
            title=_t.get("settings.next_set.title", locale=interaction.guild_locale),
            description=_t.get(
                "settings.level.buttons.button.setting_alerts.instruction",
                locale=interaction.guild_locale
            )
        )

        await interaction.response.send_message(
            embed=embed, view=self.IncludeButtons(
                interaction=interaction, last_message=interaction.message
            ), ephemeral=True
        )

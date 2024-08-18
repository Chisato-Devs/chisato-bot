from typing import Self

from disnake import MessageInteraction, ui, SelectOption, errors, ChannelType, ApplicationCommandInteraction, Member, \
    Message

from utils.basic import EmbedUI, View, EmbedErrorUI
from utils.consts import ERROR_EMOJI, SUCCESS_EMOJI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import EndView, BackButton
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class LogsModule(View, SettingModule):
    __slots__ = (
        "bot",
        "option",
        "status",
        "_members_status",
        "_server_status",
        "_channel_status",
        "_messages_status",
        "_automod_status",
        "__end", "__db_object",
        "__interaction"
    )

    def __init__(
            self,
            interaction: ApplicationCommandInteraction | MessageInteraction,
            member: Member
    ) -> None:
        self.option: SelectOption | None = None
        self._members_status = False
        self._server_status = False
        self._channel_status = False
        self._messages_status = False
        self._automod_status = False

        self.status = False
        self.bot: "ChisatoBot" = interaction.bot  # type: ignore

        self.__end = False
        self.__db_object = None
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
        await interaction.response.edit_message(embed=EmbedUI(
            title=_t.get("settings.logs.title", locale=interaction.guild_locale),
            description=_t.get("settings.logs.embed.description", locale=interaction.guild_locale)
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
            return None

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.settings.get_logs_settings(guild=self.__interaction.guild)

        self._server_status = True if data_obj and data_obj[1] else False
        self._channel_status = True if data_obj and data_obj[2] else False
        self._members_status = True if data_obj and data_obj[3] else False
        self._messages_status = True if data_obj and data_obj[4] else False
        self._automod_status = True if data_obj and data_obj[5] else False
        self.status = self._members_status or self._server_status or self._channel_status or self._messages_status

        self.__db_object = data_obj

        self.set_options()
        self.set_buttons()

        option_label = _t.get(
            "settings.logs.option.disable" if self.status
            else "settings.logs.option.enable",
            locale=self.__interaction.guild_locale
        )
        self.option = SelectOption(
            label=option_label,
            value=self.__class__.__name__,
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI
        )

        return self

    def set_options(self) -> None:
        self.logs_switch_callback.options = [
            SelectOption(
                label=_t.get(
                    f"settings.logs.selector.option.member.{'disable' if self._members_status else 'enable'}",
                    locale=self.__interaction.guild_locale
                ),
                emoji=SUCCESS_EMOJI if self._members_status else ERROR_EMOJI,
                value="MembersStatus"
            ),
            SelectOption(
                label=_t.get(
                    f"settings.logs.selector.option.guild.{'disable' if self._server_status else 'enable'}",
                    locale=self.__interaction.guild_locale
                ),
                emoji=SUCCESS_EMOJI if self._server_status else ERROR_EMOJI,
                value="ChangeServerStatus"
            ),
            SelectOption(
                label=_t.get(
                    f"settings.logs.selector.option.voice.{'disable' if self._channel_status else 'enable'}",
                    locale=self.__interaction.guild_locale
                ),
                emoji=SUCCESS_EMOJI if self._channel_status else ERROR_EMOJI,
                value="VoicesStatus"
            ),
            SelectOption(
                label=_t.get(
                    f"settings.logs.selector.option.messages.{'disable' if self._messages_status else 'enable'}",
                    locale=self.__interaction.guild_locale
                ),
                emoji=SUCCESS_EMOJI if self._messages_status else ERROR_EMOJI,
                value="MessagesStatus"
            ),
            SelectOption(
                label=_t.get(
                    f"settings.logs.selector.option.automod.{'disable' if self._automod_status else 'enable'}",
                    locale=self.__interaction.guild_locale
                ),
                emoji=SUCCESS_EMOJI if self._automod_status else ERROR_EMOJI,
                value="AutomodStatus"
            )
        ]

    def set_buttons(self) -> None:
        self.all_logs.label = _t.get(
            f"settings.logs.selector.button.label.{'disable' if self.status else 'enable'}",
            locale=self.__interaction.guild_locale
        )
        self.all_logs.emoji = SUCCESS_EMOJI if self.status else ERROR_EMOJI

    class IncludeSelect(View):
        def __init__(self, interaction: MessageInteraction, log_type: str, last_message: Message) -> None:
            self.__interaction = interaction
            self.__last: Message = last_message
            self.__end = False
            self.__log_type = log_type

            self.bot: 'ChisatoBot' = interaction.bot  # type: ignore

            super().__init__(
                author=interaction.author, timeout=300,
                store=_t, interaction=interaction
            )

        @ui.channel_select(
            placeholder="settings.logs.selector.channel_select.placeholder",
            custom_id="SelectChannelToSendLogs", channel_types=[ChannelType.text]
        )
        async def select_channel_callback(self, select: ui.ChannelSelect, interaction: MessageInteraction) -> None:
            self.__end = True
            await self.bot.databases.settings.get_logs_settings(guild=interaction.guild)
            embed = None

            match self.__log_type:
                case "MembersStatus":
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild, members_status=select.values[0].id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.member",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )
                case "ChangeServerStatus":
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild, server_status=select.values[0].id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.guild",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )
                case "VoicesStatus":
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild, channels_status=select.values[0].id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.voice",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )
                case "MessagesStatus":
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild, messages_status=select.values[0].id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.messages",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )
                case "AutomodStatus":
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild, automod_status=select.values[0].id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.automod",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )
                case "All":
                    channel_id = select.values[0].id
                    await self.bot.databases.settings.switch_logs(
                        guild=interaction.guild,
                        channels_status=channel_id,
                        members_status=channel_id,
                        messages_status=channel_id,
                        automod_status=channel_id,
                        server_status=channel_id
                    )

                    embed = EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.logs.selector.selected.all",
                            locale=interaction.guild_locale,
                            values=(
                                interaction.author.mention, interaction.author.name,
                                select.values[0].mention, select.values[0].name
                            )
                        )
                    )

            og_embed = EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.logs.selector.success.changed_channel",
                    locale=interaction.guild_locale
                )
            )

            try:
                await self.__last.edit(
                    embed=embed, view=EndView(
                        author=interaction.author, interaction=self.__interaction
                    )
                )
            except errors.Forbidden or errors.HTTPException:
                og_embed = EmbedErrorUI(
                    description=_t.get(
                        "settings.logs.selector.error.previous_message_deleted",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )

            try:
                await interaction.response.edit_message(embed=og_embed, view=None)
            except errors.HTTPException or errors.Forbidden:
                pass

    @ui.string_select(
        placeholder="settings.logs.selector.placeholder",
        custom_id="LogsSwitchSelect",
        options=[
            SelectOption(
                label="Чето сдохло"
            )
        ]
    )
    async def logs_switch_callback(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()

        def get_embed(log_name: str) -> EmbedUI:
            return EmbedUI(
                title=_t.get("settings.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.logs.selector.callback.embed.description",
                    locale=interaction.guild_locale,
                    values=(_t.get(log_name, locale=interaction.guild_locale),)
                )
            )

        match select.values[0]:
            case "MembersStatus":
                if not self._members_status:
                    return await interaction.response.send_message(
                        embed=get_embed("settings.logs.selector.callback.embed.part.1"), view=self.IncludeSelect(
                            interaction=interaction, log_type=select.values[0], last_message=interaction.message
                        ), ephemeral=True
                    )

                await self.bot.databases.settings.switch_logs(guild=interaction.guild, members_status=False)
            case "ChangeServerStatus":
                if not self._server_status:
                    return await interaction.response.send_message(
                        embed=get_embed("settings.logs.selector.callback.embed.part.2"), view=self.IncludeSelect(
                            interaction=interaction, log_type=select.values[0], last_message=interaction.message
                        ), ephemeral=True
                    )

                await self.bot.databases.settings.switch_logs(guild=interaction.guild, server_status=False)
            case "VoicesStatus":
                if not self._channel_status:
                    return await interaction.response.send_message(
                        embed=get_embed("settings.logs.selector.callback.embed.part.3"), view=self.IncludeSelect(
                            interaction=interaction, log_type=select.values[0], last_message=interaction.message
                        ), ephemeral=True
                    )

                await self.bot.databases.settings.switch_logs(guild=interaction.guild, channels_status=False)
            case "MessagesStatus":
                if not self._messages_status:
                    return await interaction.response.send_message(
                        embed=get_embed("settings.logs.selector.callback.embed.part.4"), view=self.IncludeSelect(
                            interaction=interaction, log_type=select.values[0], last_message=interaction.message
                        ), ephemeral=True
                    )

                await self.bot.databases.settings.switch_logs(guild=interaction.guild, messages_status=False)
            case "AutomodStatus":
                if not self._automod_status:
                    return await interaction.response.send_message(
                        embed=get_embed("settings.logs.selector.callback.embed.part.5"), view=self.IncludeSelect(
                            interaction=interaction, log_type=select.values[0], last_message=interaction.message
                        ), ephemeral=True
                    )

                await self.bot.databases.settings.switch_logs(guild=interaction.guild, automod_status=False)

        await self.initialize_database()
        await interaction.response.edit_message(view=self)

    @ui.button(
        label="settings.logs.button.refresh.label",
        emoji="<:Refresh3:1114986806480478318>",
        custom_id="RefreshMessageLogs"
    )
    async def refresh_message(self, _, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()
        await interaction.response.edit_message(view=self)

    @ui.button(
        label="Чета сдохло", custom_id="AllLogs"
    )
    async def all_logs(self, _, interaction: MessageInteraction) -> None:
        await self.initialize_database()

        if self.status:
            await self.bot.databases.settings.switch_logs(
                guild=interaction.guild, members_status=False, server_status=False,
                channels_status=False, messages_status=False
            )

            await self.initialize_database()
            await interaction.response.edit_message(
                view=self
            )
        else:
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("settings.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "settings.logs.button.all.embed.description",
                        locale=interaction.guild_locale
                    )
                ), view=self.IncludeSelect(
                    interaction=interaction, log_type="All", last_message=interaction.message
                ), ephemeral=True
            )

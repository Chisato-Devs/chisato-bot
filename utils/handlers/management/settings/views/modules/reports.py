from typing import TYPE_CHECKING, Self

from disnake import Member, MessageInteraction, ChannelType, SelectOption, \
    errors, TextChannel, ui, ApplicationCommandInteraction

from utils.basic import EmbedUI, View, EmbedErrorUI
from utils.consts import ERROR_EMOJI, SUCCESS_EMOJI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton, EndView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class ReportsModule(View, SettingModule):
    __slots__ = (
        "status",
        "bot",
        "option",
        "__end",
        "__interaction"
    )

    def __init__(
            self,
            member: Member,
            interaction: MessageInteraction | ApplicationCommandInteraction
    ) -> None:
        self.status: bool = False
        self.bot: ChisatoBot = interaction.bot  # type: ignore
        self.option: SelectOption | None = None

        self.__end = False
        self.__interaction = interaction

        super().__init__(
            author=member, timeout=300, store=_t,
            interaction=interaction
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
                title=_t.get("settings.reports.title", locale=interaction.guild_locale),
                description=_t.get("settings.reports.embed.description", locale=interaction.guild_locale)
            ),
            view=self
        )

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.settings.get(guild=self.__interaction.guild.id)

        self.status = True if data_obj and data_obj[1] else False
        self.option = SelectOption(
            label=_t.get(
                "settings.reports.option." + ("disable" if self.status else "enable"),
                locale=self.__interaction.guild_locale
            ),
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI,
            value=self.__class__.__name__
        )

        return self

    async def on_timeout(self) -> None:
        if not self.__end:
            self.button_disables(
                custom_ids=['channel_for_reports', 'off_report_settings', 'back_reports_button'],
                disabled=True
            )

            try:
                await self.__interaction.edit_original_response(view=self)
            except errors.InteractionResponded:
                return None
            except errors.HTTPException:
                return None
            return None

    @ui.channel_select(
        placeholder="settings.reports.selector.placeholder", row=0,
        channel_types=[ChannelType.text], custom_id='channel_for_reports'
    )
    async def select_channel_callable(self, select: ui.ChannelSelect, interaction: MessageInteraction) -> None:
        self.__end = True
        report_channel: TextChannel = select.values[0]

        if await self.bot.databases.moderation.add_global_reports_settings(
                guild=interaction.guild, channel=select.values[0]
        ):
            embed = EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                timestamp=interaction.created_at,
                description=_t.get(
                    "settings.reports.selector.callback.enable", locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, interaction.author.name,
                        report_channel.mention, report_channel.name
                    )
                )
            )

        else:
            embed = EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.reports.selector.callback.change", locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, interaction.author.name,
                        report_channel.mention, report_channel.name
                    )
                ),
                timestamp=interaction.created_at
            )

        await interaction.response.edit_message(
            embed=embed, view=EndView(
                author=interaction.author, interaction=interaction
            )
        )

    @ui.button(
        label="settings.reports.button.disable.label",
        emoji=ERROR_EMOJI, row=1,
        custom_id="off_report_settings"
    )
    async def off_callable(self, _, interaction: MessageInteraction) -> None:
        self.__end = True
        status = await self.bot.databases.moderation.remove_global_reports_settings(guild=interaction.guild)

        if status:
            embed = EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.reports.button.disable.embed.description",
                    locale=interaction.guild_locale,
                    values=(interaction.author.mention, interaction.author.name)
                ),
                timestamp=interaction.created_at
            )

            await interaction.response.edit_message(
                embed=embed, view=EndView(
                    author=interaction.author, interaction=interaction
                )
            )
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "settings.reports.button.error.reports_disabled",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

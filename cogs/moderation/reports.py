import re
from datetime import datetime
from re import sub
from typing import Literal, Type, TYPE_CHECKING

from disnake import (
    MessageInteraction,
    TextChannel,
    MessageCommandInteraction,
    Message,
    Member,
    TextInputStyle,
    ModalInteraction,
    Forbidden,
    HTTPException, Embed, ApplicationCommandInteraction, Localized
)
from disnake.ext.commands import message_command, Param
from disnake.ui import button, Modal, TextInput
from disnake.utils import format_dt

from utils.basic import EmbedUI, EmbedErrorUI, CogUI, View
from utils.handlers.moderation import time_converter, close_report
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

PunishmentType: Type[str] = Literal["ban", "warn", "timeout", "kick"]
_t = ChisatoLocalStore.load(__file__)


class ReportReasonModal(Modal):
    def __init__(
            self, reporter: Member, message: Message, channel: TextChannel, bot: "ChisatoBot",
            interaction: MessageInteraction | ApplicationCommandInteraction
    ) -> None:
        self.reporter: Member = reporter
        self.locale = interaction.guild_locale
        self.message: Message = message
        self.channel: TextChannel = channel
        self.bot = bot

        components: list[TextInput] = [
            TextInput(
                label=_t.get("reports.modal.report_reason.option.label", locale=self.locale),
                placeholder=_t.get("reports.modal.report_reason.option.placeholder", locale=self.locale),
                custom_id="inputted_report_reason",
                style=TextInputStyle.paragraph,
                max_length=256,
            )
        ]
        super().__init__(title=_t.get("reports.modal.report_reason.title", locale=self.locale), components=components)

    async def callback(self, interaction: ModalInteraction) -> None:
        inputted_reason: str = interaction.text_values['inputted_report_reason']

        embed: EmbedUI = EmbedUI(
            title=_t.get("reports.title", locale=interaction.guild_locale),
            description=_t.get(
                "reports.modal.report_reason.callback.embed.description", locale=interaction.guild_locale,
                values=(
                    self.reporter.mention, self.reporter, self.message.author.mention, self.message.author,
                    self.message.jump_url, self.message.channel, inputted_reason
                )
            )
        ).set_footer(
            icon_url="https://cdn.discordapp.com/emojis/1114365034999578634.webp?size=256",
            text=_t.get(
                "reports.warning.footer",
                interaction.guild_locale
            )
        )

        if self.message.content:
            embed.description += _t.get(
                "reports.modal.report_reason.callback.embed.description.part.1", locale=interaction.guild_locale,
                values=(self.message.content,)
            )

        if self.message.attachments:
            attachments: str = " | ".join(
                f"[{attachment.filename}]({attachment.url})" for attachment in self.message.attachments
            )

            embed.description += _t.get(
                "reports.modal.report_reason.callback.embed.description.part.2", locale=interaction.guild_locale,
                values=(attachments,)
            )

        await self.channel.send(
            embed=embed, view=ReportInteractionButtons(message=self.message, reason=inputted_reason)
        )

        embed.remove_footer()
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PunishmentSettingsButton(View):
    def __init__(
            self, message: Message,
            report_message: Message,
            reason: str, bot: 'ChisatoBot',
            punishment_type: PunishmentType,
            punishment_duration: datetime = None,
            punishment_duration_str: str = None,
    ) -> None:
        self.bot = bot

        self.intruder: Member = message.author
        self.message: Message = message
        self.report_message: Message = report_message
        self.reason: str = reason
        self.punishment_type: PunishmentType = punishment_type
        self.punishment_duration: datetime | None = punishment_duration
        self.punishment_duration_str: str | None = punishment_duration_str

        super().__init__(timeout=None, store=_t, guild=message.guild)

    @button(label="reports.button.custom_error.label", emoji="<:Edit:1116358712794296460>", row=1)
    async def handle_custom_reason(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(modal=CustomPunishmentModal(self, interaction))

    @button(label="reports.button.confirm.label", emoji="<:Success:1113824546911440956>", row=3)
    async def handle_confirm(self, _, interaction: MessageInteraction) -> None:
        match self.punishment_type:
            case "ban":
                if not [role for role in interaction.author.roles if role.permissions.ban_members]:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.setting.error.doesnt_have_need_permission", locale=interaction.guild_locale),
                        interaction.author
                    )

                    return await interaction.response.edit_message(embed=embed, view=None)
                try:
                    await self.intruder.ban(reason=self.reason)
                except Forbidden:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.forbidden", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                except HTTPException:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.http", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    await self.bot.databases.moderation.add_global_ban(
                        guild=interaction.guild,
                        member=self.intruder,
                        moderator=interaction.author,
                        reason=self.reason,
                        unban_time=self.punishment_duration,
                        locale=interaction.guild_locale
                    )

                    cool_time: str = format_dt(self.punishment_duration)
                    embed: EmbedUI = EmbedUI(
                        title=_t.get("ban.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "reports.button.confirm.callback.case.ban.success", locale=interaction.guild_locale,
                            values=(
                                self.intruder.mention, self.intruder, interaction.author.mention, interaction.author,
                                self.message.jump_url, self.message.channel, cool_time, self.punishment_duration_str,
                                self.reason
                            )
                        )
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                    await self.message.channel.send(embed=embed)
                    await close_report(
                        report_message=self.report_message,
                        member=interaction.author,
                        status=True,
                        verdict="ban",
                        interaction=interaction
                    )
            case "warn":
                if not [role for role in interaction.author.roles if role.permissions.view_audit_log]:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.setting.error.doesnt_have_need_permission", locale=interaction.guild_locale),
                        interaction.author
                    )

                    return await interaction.response.edit_message(embed=embed, view=None)

                embed: EmbedUI | EmbedErrorUI = await self.bot.databases.moderation.add_global_warn(
                    guild=interaction.guild,
                    member=self.intruder,
                    moderator=interaction.author,
                    reason=self.reason,
                    message=self.message,
                    by_report=True,
                    locale=interaction.guild_locale
                )

                if isinstance(embed, EmbedErrorUI):
                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    await interaction.response.edit_message(embed=embed, view=None)
                    await self.message.channel.send(embed=embed)
                    await close_report(
                        report_message=self.report_message,
                        member=interaction.author,
                        status=True,
                        verdict="warn",
                        interaction=interaction
                    )
            case "timeout":
                if not [role for role in interaction.author.roles if role.permissions.moderate_members]:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.setting.error.doesnt_have_need_permission", locale=interaction.guild_locale),
                        interaction.author
                    )

                    return await interaction.response.edit_message(embed=embed, view=None)

                try:
                    await self.intruder.timeout(until=self.punishment_duration, reason=self.reason)
                except Forbidden:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.forbidden", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                except HTTPException:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.http", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    cool_time: str = format_dt(self.punishment_duration)
                    embed: EmbedUI = EmbedUI(
                        title=_t.get("timeout.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "reports.button.confirm.callback.case.timeout.success", locale=interaction.guild_locale,
                            values=(
                                self.intruder.mention, self.intruder, interaction.author.mention, interaction.author,
                                self.message.jump_url, self.message.channel, cool_time, self.punishment_duration_str,
                                self.reason
                            )
                        )
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                    await self.message.channel.send(embed=embed)
                    await close_report(
                        report_message=self.report_message,
                        member=interaction.author,
                        status=True,
                        verdict="timeout",
                        interaction=interaction
                    )
            case "kick":
                if not [role for role in interaction.author.roles if role.permissions.kick_members]:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.setting.error.doesnt_have_need_permission", locale=interaction.guild_locale),
                        interaction.author
                    )

                    return await interaction.response.edit_message(embed=embed, view=None)

                try:
                    await self.intruder.kick(reason=self.reason)
                except Forbidden:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.forbidden", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                except HTTPException:
                    embed: EmbedErrorUI = EmbedErrorUI(
                        _t.get("reports.button.confirm.callback.error.http", locale=interaction.guild_locale),
                        interaction.author
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    embed: EmbedUI = EmbedUI(
                        title=_t.get("kick.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "reports.button.confirm.callback.case.kick.success", locale=interaction.guild_locale,
                            values=(
                                self.intruder.mention, self.intruder, interaction.author.mention, interaction.author,
                                self.message.jump_url, self.message.channel, self.reason
                            )
                        )
                    )

                    await interaction.response.edit_message(embed=embed, view=None)
                    await self.message.channel.send(embed=embed)
                    await close_report(
                        report_message=self.report_message,
                        member=interaction.author,
                        status=True,
                        verdict="kick",
                        interaction=interaction
                    )


class CustomPunishmentModal(Modal):
    def __init__(self, punishment_settings: PunishmentSettingsButton, interaction: MessageInteraction) -> None:
        self.punishment_settings: PunishmentSettingsButton = punishment_settings

        super().__init__(
            title=_t.get("reports.modal.custom_punishment.title", locale=interaction.guild_locale),
            components=[
                TextInput(
                    label=_t.get(
                        "reports.modal.custom_punishment.component.label", locale=interaction.guild_locale
                    ),
                    placeholder=_t.get(
                        "reports.modal.custom_punishment.component.placeholder", locale=interaction.guild_locale
                    ),
                    custom_id="inputted_custom_punishment_reason",
                    style=TextInputStyle.paragraph,
                    max_length=256,
                )
            ]
        )

    async def callback(self, interaction: ModalInteraction) -> None:
        inputted_reason: str = interaction.text_values['inputted_custom_punishment_reason']
        self.punishment_settings.reason = inputted_reason

        embed: Embed = interaction.message.embeds[0]
        embed.description = sub(
            f"> \*\*{_t.get('reports.reason', locale=interaction.guild_locale)}:\*\* `.*`",
            _t.get(
                "reports.modal.custom_punishment.callback.sub.repl", locale=interaction.guild_locale,
                values=(inputted_reason,)
            ),
            embed.description
        )

        await interaction.response.edit_message(embed=embed)


class PunishmentTimeModal(Modal):
    def __init__(
            self, message: Message, reason: str, punishment_type: PunishmentType,
            interaction: MessageInteraction
    ) -> None:
        self.message: Message = message
        locale = interaction.guild_locale
        self.reason: str = reason
        self.punishment_type: PunishmentType = punishment_type

        components: list[TextInput] = [
            TextInput(
                label=_t.get("reports.modal.punishment_time.component.label", locale=locale),
                placeholder=_t.get("reports.modal.punishment_time.component.placeholder", locale=locale),
                custom_id="inputted_punishment_time",
                style=TextInputStyle.short,
                max_length=50,
            ),
        ]
        super().__init__(
            title=_t.get("reports.modal.punishment_time.title", locale=locale),
            components=components
        )

    async def callback(self, interaction: ModalInteraction) -> None:
        inputted_punishment_time: str = interaction.text_values['inputted_punishment_time']

        result: datetime | EmbedErrorUI = await time_converter(
            inputted_punishment_time,
            interaction.author,
            self.punishment_type == "timeout",
            interaction.guild_locale
        )

        if isinstance(result, datetime):
            match self.punishment_type:
                case "timeout":
                    title = _t.get("timeout.title", locale=interaction.guild_locale)
                case _:
                    title = _t.get("ban.title", locale=interaction.guild_locale)

            embed: EmbedUI = EmbedUI(
                title=title,
                description=_t.get(
                    "reports.setting.punishment", locale=interaction.guild_locale,
                    values=(
                        self.message.author.mention, self.message.author,
                        self.reason
                    )
                )
            )

            await interaction.response.send_message(
                embed=embed,
                view=PunishmentSettingsButton(
                    message=self.message,
                    report_message=interaction.message,
                    reason=self.reason,
                    bot=interaction.bot,  # type: ignore
                    punishment_type=self.punishment_type,
                    punishment_duration=result,
                    punishment_duration_str=inputted_punishment_time
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(embed=result, ephemeral=True)


class ReportInteractionButtons(View):
    def __init__(self, message: Message, reason: str) -> None:
        self.message: Message = message
        self.reason: str = reason
        super().__init__(timeout=None, store=_t, guild=message.guild)

    @button(emoji="<:removeuser:1114369700554621010>", row=1)
    async def kick_intruder(self, _, interaction: MessageInteraction) -> None:
        embed: EmbedUI = EmbedUI(
            title=_t.get("kick.title", locale=interaction.guild_locale),
            description=_t.get(
                "reports.setting.punishment", locale=interaction.guild_locale,
                values=(
                    self.message.author.mention, self.message.author,
                    self.reason
                )
            )
        )

        await interaction.response.send_message(
            embed=embed,
            view=PunishmentSettingsButton(
                message=self.message,
                report_message=interaction.message,
                reason=self.reason,
                punishment_type="kick",
                bot=interaction.bot  # type: ignore
            ),
            ephemeral=True
        )

    @button(emoji="<:Volumemuted:1158170369019101305>", row=1)
    async def timeout_intruder(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            modal=PunishmentTimeModal(
                interaction=interaction,
                message=self.message,
                reason=self.reason,
                punishment_type="timeout"
            )
        )

    @button(emoji="<:ProtectionOFF:1114647772440821954>", row=1)
    async def warn_intruder(self, _, interaction: MessageInteraction) -> None:
        embed: EmbedUI = EmbedUI(
            title=_t.get("warn.title", locale=interaction.guild_locale),
            description=_t.get(
                "reports.setting.punishment", locale=interaction.guild_locale,
                values=(
                    self.message.author.mention, self.message.author,
                    self.reason
                )
            )
        )

        await interaction.response.send_message(
            embed=embed,
            view=PunishmentSettingsButton(
                message=self.message,
                report_message=interaction.message,
                reason=self.reason,
                punishment_type="warn",
                bot=interaction.bot  # type: ignore
            ),
            ephemeral=True
        )

    @button(emoji="<:Userrestricted:1158170389063663617>", row=1)
    async def ban_intruder(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            modal=PunishmentTimeModal(
                interaction=interaction,
                message=self.message,
                reason=self.reason,
                punishment_type="ban"
            )
        )

    @button(label="reports.button.decline_report", emoji="<:Trashcan:1114376699027660820>", row=2)
    async def decline_report(self, _, interaction: MessageInteraction) -> None:
        await close_report(
            report_message=interaction.message, member=interaction.author, status=False,
            interaction=interaction
        )


class ReportCog(CogUI):
    DISCORD_MESSAGE_REGEX = re.compile("https://discord\.com/channels/(\d+)/(\d+)/(\d+)")

    async def backend_logic(
            self,
            interaction: ApplicationCommandInteraction | MessageCommandInteraction,
            message: Message
    ) -> None:
        if message.author.bot:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.command.callback.error.not_bot",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )

        channel_id: int | None = await self.bot.databases.moderation.get_global_reports_settings(
            guild=interaction.guild
        )
        if not channel_id:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.message_command.callback.error.report_is_not_defined",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )

        channel: TextChannel | None = interaction.guild.get_channel(channel_id)
        member: Member | None = interaction.guild.get_member(message.author.id)

        if member is None:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get(
                    "reports.message_command.callback.error.not_found_member",
                    locale=interaction.guild_locale
                ),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif channel is None:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.message_command.callback.error.not_found_channel",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_modal(
                modal=ReportReasonModal(
                    interaction=interaction,
                    reporter=interaction.author,
                    message=message,
                    channel=channel,
                    bot=self.bot
                )
            )

    @CogUI.slash_command(
        name="report",
        description=Localized(
            "📝 Репорт: отправка жалобы на пользователя.",
            data=_t.get("reports.command.description")
        )
    )
    async def do_report_cmd(
            self,
            interaction: ApplicationCommandInteraction,
            message_url: str = Param(
                name=Localized(
                    "ссылка",
                    data=_t.get("reports.command.option.url.name")
                ),
                description=Localized(
                    "- укажи ссылку на сообщение",
                    data=_t.get("reports.command.option.url.description")
                )
            )
    ) -> None:
        search_result = self.DISCORD_MESSAGE_REGEX.match(message_url)
        if not search_result:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.message_command.callback.error.unknown_url",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )

        channel_id: int = search_result.group(2)
        message_id: int = search_result.group(3)

        if not (channel := interaction.guild.get_channel(int(channel_id))):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.message_command.callback.error.not_found_channel",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )

        message: Message = await channel.get_partial_message(message_id).fetch()
        if not message:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get(
                        "reports.message_command.callback.error.not_found_message",
                        locale=interaction.guild_locale
                    ),
                    interaction.author
                ),
                ephemeral=True
            )

        return await self.backend_logic(interaction, message)

    @message_command(
        name=Localized(
            "Пожаловаться",
            data=_t.get("reports.message_command.name")
        )
    )
    async def do_report(self, interaction: MessageCommandInteraction, message: Message) -> None:
        return await self.backend_logic(interaction, message)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(ReportCog(bot))

from datetime import datetime
from typing import TYPE_CHECKING

from disnake import MessageCommandInteraction, MessageInteraction, Member, Forbidden, HTTPException, \
    Localized
from disnake.ext.commands import Param
from disnake.ui import button
from disnake.utils import format_dt

from utils.basic import EmbedErrorUI, EmbedUI, CogUI, CommandsPermission, View
from utils.handlers.moderation import time_converter
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class MemberCurrentTimeoutedButton(View):
    def __init__(
            self, author: Member, member: Member, time: datetime,
            time_str: str, reason: str, bot: "ChisatoBot"
    ) -> None:
        self.bot = bot

        self.author: Member = author
        self.member: Member = member
        self.time: datetime = time
        self.time_str: str = time_str
        self.reason: str = reason

        super().__init__(timeout=None, author=author, store=_t)

    @button(label="timeout.button.label", emoji="<:Success:1113824546911440956>")
    async def timeout_success_on_timeouted(self, _, interaction: MessageInteraction) -> None:
        try:
            await self.member.timeout(until=self.time, reason=self.reason)
        except Forbidden:
            await interaction.response.edit_message(
                embed=EmbedErrorUI(
                    _t.get("timeout.error.forbidden", locale=interaction.guild_locale),
                    interaction.author
                )
            )
        except HTTPException:
            await interaction.response.edit_message(
                embed=EmbedErrorUI(
                    _t.get("timeout.error.http", locale=interaction.guild_locale),
                    interaction.author
                )
            )
        else:
            cool_time: str = format_dt(self.time)
            embed: EmbedUI = EmbedUI(
                title=_t.get("timeout.title", locale=interaction.guild_locale),
                description=_t.get(
                    "timeout.give.success", locale=interaction.guild_locale,
                    values=(
                        self.member.mention, self.member, interaction.author.mention,
                        interaction.author, cool_time, self.time_str, self.reason
                    )
                )
            )

            await self.bot.databases.moderation.add_user_moderation_stats(
                guild=interaction.guild,
                member=self.author,
                punishment="timeout",
                is_given=True
            )

            await self.bot.databases.moderation.add_user_moderation_stats(
                guild=interaction.guild,
                member=self.member,
                punishment="timeout",
                is_given=False
            )
            await interaction.response.edit_message(embed=embed, view=None)


class TimeoutCog(CogUI):

    @CogUI.slash_command(name="timeout")
    async def __timeout(self, interaction: MessageCommandInteraction) -> None:
        ...

    @__timeout.sub_command(
        name="add",
        description=Localized(
            "🔇 Мут: ограничение права пользователя на взаимодействие с сервером.",
            data=_t.get("timeout.command.add.description")
        )
    )
    @CommandsPermission.decorator(moderate_members=True)
    async def add_timeout(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("timeout.command.add.option.member.name")),
                description=Localized(
                    "- укажи пользователя, которому хочешь выдать тайм-аут.",
                    data=_t.get("timeout.command.add.option.member.description")
                )
            ),
            time: str = Param(
                name=Localized("время", data=_t.get("timeout.command.add.option.time.name")),
                description=Localized(
                    "- укажи время тайм-аута в формате, например, '1h' для 1 часа.",
                    data=_t.get("timeout.command.add.option.time.description")
                ),
                default='1h'
            ),
            reason: str = Param(
                name=Localized("причина", data=_t.get("timeout.command.add.option.reason.name")),
                description=Localized(
                    "- укажи причину выдачи тайм-аута.",
                    data=_t.get("timeout.command.add.option.reason.description")
                ),
                default="None"
            )
    ) -> None:
        if reason == "None":
            reason = _t.get("timeout.command.add.option.reason.default", locale=interaction.guild_locale)
        if member == interaction.author:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("timeout.error.member_is_not_you", locale=interaction.guild_locale),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif member.bot:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("timeout.error.not_bot", locale=interaction.guild_locale),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            result: datetime | EmbedErrorUI = await time_converter(
                time=time, member=interaction.author, timeout=True, locale=interaction.guild_locale
            )
            if isinstance(result, datetime):
                if member.current_timeout:
                    cool_time: str = format_dt(member.current_timeout)
                    embed: EmbedUI = EmbedUI(
                        title=_t.get("timeout.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "timeout.error.error.has_timeout",
                            locale=interaction.guild_locale, values=(cool_time,)
                        )
                    ).set_footer(
                        text=_t.get(
                            "timeout.error.error.has_timeout.footer",
                            locale=interaction.guild_locale
                        )
                    )

                    await interaction.response.send_message(
                        embed=embed,
                        view=MemberCurrentTimeoutedButton(
                            author=interaction.author,
                            member=member,
                            time=result,
                            time_str=time,
                            reason=reason,
                            bot=self.bot
                        ),
                    )
                else:
                    try:
                        await member.timeout(until=result, reason=reason)
                    except Forbidden:
                        embed: EmbedErrorUI = EmbedErrorUI(
                            _t.get("timeout.error.forbidden", locale=interaction.guild_locale),
                            interaction.author
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    except HTTPException:
                        embed: EmbedErrorUI = EmbedErrorUI(
                            _t.get("timeout.error.http", locale=interaction.guild_locale),
                            interaction.author
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        cool_time: str = format_dt(result)
                        embed: EmbedUI = EmbedUI(
                            title=_t.get("timeout.title", locale=interaction.guild_locale),
                            description=_t.get(
                                "timeout.give.success", locale=interaction.guild_locale,
                                values=(
                                    member.mention, member.name, interaction.author.mention, interaction.author.name,
                                    cool_time, time, reason
                                )
                            )
                        )
                        await interaction.response.send_message(embed=embed)

                        await self.bot.databases.moderation.add_user_moderation_stats(
                            guild=interaction.guild,
                            member=interaction.author,
                            punishment="timeout",
                            is_given=True
                        )

                        await self.bot.databases.moderation.add_user_moderation_stats(
                            guild=interaction.guild,
                            member=member,
                            punishment="timeout",
                            is_given=False
                        )

            else:
                await interaction.response.send_message(embed=result, ephemeral=True)

    @__timeout.sub_command(
        name="remove",
        description=Localized(
            "🔊 Снять мут: восстановление права пользователя на взаимодействие с сервером.",
            data=_t.get("timeout.command.remove.description")
        )
    )
    @CommandsPermission.decorator(moderate_members=True)
    async def remove_timeout(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("timeout.command.remove.option.member.name")),
                description=Localized(
                    "- укажи пользователя, у которого хочешь удалить тайм-аут.",
                    data=_t.get("timeout.command.remove.option.member.name")
                )
            ),
            reason: str = Param(
                name=Localized("причина", data=_t.get("timeout.command.remove.option.reason.name")),
                description=Localized(
                    "- укажи причину удаления тайм-аута.",
                    data=_t.get("timeout.command.remove.option.reason.description")
                ),
                default="None"
            )
    ) -> None:
        if reason == "None":
            reason = _t.get("timeout.command.remove.option.reason.default", locale=interaction.guild_locale)
        if member == interaction.author:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("timeout.error.not_self", locale=interaction.guild_locale),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif not member.current_timeout:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("timeout.error.not_timeout", locale=interaction.guild_locale),
                interaction.author
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            try:
                await member.timeout(until=None, reason=reason)
            except Forbidden:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("timeout.error.remove.forbidden", locale=interaction.guild_locale),
                    interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except HTTPException:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("timeout.error.remove.http", locale=interaction.guild_locale), interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed: EmbedUI = EmbedUI(
                    title=_t.get("timeout.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "timeout.success.remove_timeout", locale=interaction.guild_locale,
                        values=(
                            member.mention, member, interaction.author.mention,
                            interaction.author, reason
                        )
                    )
                )

                await interaction.response.send_message(embed=embed)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(TimeoutCog(bot))

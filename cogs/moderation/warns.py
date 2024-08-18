from typing import TYPE_CHECKING

from disnake import MessageCommandInteraction, Member, Localized
from disnake.ext.commands import Param
from disnake.utils import format_dt

from utils.basic import EmbedErrorUI, EmbedUI, CogUI, CommandsPermission
from utils.handlers.moderation import RemoveWarningButton
from utils.handlers.pagination import PaginatorView, DeleteMessageButton
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class WarningsCog(CogUI):

    @CogUI.slash_command(name="warnings")
    async def __warn(self, interaction: MessageCommandInteraction) -> None:
        ...

    @CogUI.slash_command(name="moderation")
    async def __moderation(self, interaction: MessageCommandInteraction) -> None:
        ...

    @__warn.sub_command(
        name="warn", description=Localized(
            "🛑 Варн: выдача предупреждения пользователю.",
            data=_t.get("warn.command.warn.description")
        )
    )
    @CommandsPermission.decorator(view_audit_log=True)
    async def add_warning(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("warn.command.warn.option.member.name")),
                description=Localized(
                    "- укажи участника для выдачи предупреждения",
                    data=_t.get("warn.command.warn.option.member.description")
                )
            ),
            reason: str = Param(
                name=Localized("причина", data=_t.get("warn.command.warn.option.reason.name")),
                description=Localized(
                    "- укажи причину для выдачи предупреждения",
                    data=_t.get("warn.command.warn.option.reason.description")
                )
            )
    ) -> None:
        if member == interaction.author:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "warn.command.not_self", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await interaction.response.send_message(
            embed=await self.bot.databases.moderation.add_global_warn(
                guild=interaction.guild,
                member=member, moderator=interaction.author,
                reason=reason, locale=interaction.guild_locale
            )
        )

        await self.bot.databases.moderation.add_user_moderation_stats(
            guild=interaction.guild,
            member=interaction.author,
            punishment="warn",
            is_given=True
        )

        await self.bot.databases.moderation.add_user_moderation_stats(
            guild=interaction.guild,
            member=member,
            punishment="warn",
            is_given=False
        )

    @__warn.sub_command(
        name="list-remove",
        description=Localized(
            "🛑 Варн: просмотр списка предупреждений участника и снятие предупреждений.",
            data=_t.get("warn.list_remove.command.description")
        )
    )
    @CommandsPermission.decorator(view_audit_log=True)
    async def list_warnings(
            self, interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("warn.list_remove.command.option.member")),
                description=Localized(
                    "- укажи пользователя, у которого нужно просмотреть предупреждения.",
                    data=_t.get("warn.list_remove.command.option.member.description")
                )
            )
    ) -> None:
        data: list[tuple] | None = await self.bot.databases.moderation.get_user_warns_list(
            guild=interaction.guild,
            member=member
        )

        if not data:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    _t.get("warn.error.doesnt_have_warns", locale=interaction.guild_locale),
                    interaction.author
                ),
                ephemeral=True
            )

        embeds: list = []

        for item in data:
            moderator: Member | None = interaction.guild.get_member(item[1])
            moderator_info: str = f"{moderator.mention} | `{moderator}`" if moderator else _t.get(
                "warn.not_found_user", locale=interaction.guild_locale
            )
            time: str = format_dt(item[3], style="f")

            embeds.append(
                EmbedUI(
                    title=_t.get("warn.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "warn.list_remove.description",
                        locale=interaction.guild_locale,
                        values=(
                            member.mention, member.name, moderator_info,
                            time, item[4], item[2]
                        )
                    )
                )
            )

        view = PaginatorView(
            embeds=embeds,
            author=interaction.author,
            footer=True, store=_t,
            interaction=interaction
        )
        view.add_item(DeleteMessageButton())
        view.add_item(RemoveWarningButton())

        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

    @__moderation.sub_command(
        name="stats",
        description=Localized(
            "📊 Статистика: просмотр статистики наказаний пользователя.",
            data=_t.get("warn.command.stats.description")
        )
    )
    @CommandsPermission.decorator(view_audit_log=True)
    async def stats_moderation(
            self,
            interaction: MessageCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("warn.command.stats.member.name")),
                description=Localized(
                    "- укажи пользователя, у которого хочешь просмотреть статистику.",
                    data=_t.get("warn.command.stats.member.description")
                )
            )
    ) -> None:
        embed: EmbedUI | EmbedErrorUI = await self.bot.databases.moderation.get_user_moderation_stats(
            guild=interaction.guild,
            member=member,
            author=interaction.author,
            locale=interaction.guild_locale
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(WarningsCog(bot))

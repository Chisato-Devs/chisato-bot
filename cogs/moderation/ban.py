from datetime import datetime
from typing import TYPE_CHECKING

from disnake import Member, Forbidden, NotFound, HTTPException, ApplicationCommandInteraction, User, Guild, Localized
from disnake.ext import tasks
from disnake.ext.commands import Param
from disnake.utils import format_dt

from utils.basic import EmbedUI, EmbedErrorUI, CogUI, CommandsPermission
from utils.handlers.moderation import time_converter
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class BanCog(CogUI):

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()

        self.unban_task.start()

    def cog_unload(self) -> None:
        self.unban_task.stop()

    @CogUI.slash_command(name="ban")
    async def __ban(self, interaction: ApplicationCommandInteraction) -> None:
        pass

    @tasks.loop(minutes=3)
    async def unban_task(self) -> None:
        if self.bot.user.id != 1066753199421263923:
            return

        if not hasattr(self.bot.databases, "moderation"):
            return

        bans = await self.bot.databases.moderation.get_guild_global_bans(current_time=datetime.now())
        if bans:
            for data in bans:
                guild: Guild | None = self.bot.get_guild(data[0])
                if guild is None:
                    await self.bot.databases.moderation.remove_guild_on_error_global_bans(guild_id=data[0])
                    continue
                else:
                    user: User = await self.bot.fetch_user(data[1])
                    try:
                        await guild.fetch_ban(user)
                    except (Forbidden, NotFound):
                        await self.bot.databases.moderation.remove_member_on_error_global_bans(
                            guild_id=data[0], member_id=data[1]
                        )
                    else:
                        await guild.unban(
                            user=user, reason=_t.get("ban.task.unban.label", locale=guild.preferred_locale)
                        )

    @__ban.sub_command(
        name="add", description=Localized("🚫 Бан: блокировка пользователя.", data=_t.get("ban.command.description"))
    )
    @CommandsPermission.decorator(ban_members=True)
    async def add_ban(
            self,
            interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("пользователь", key="ban.command.option.member.name"),
                description=Localized(
                    "- укажи пользователя которому хочешь выдать блокировку.",
                    key="ban.command.option.member.description"
                )
            ),
            ban_time: str = Param(
                name=Localized("длительность", key="ban.command.option.time.name"),
                description=Localized(
                    "- укажи длительность блокировки.",
                    key="ban.command.option.time.description"
                ),
                default="Never"
            ),
            reason: str = Param(
                name=Localized("причина", key="ban.command.option.reason.name"),
                description=Localized("- укажи причину блокировки.", key="ban.command.option.reason.description"),
                default="None"
            )
    ) -> None:
        if reason is None:
            reason = _t.get("ban.command.option.reason.default", locale=interaction.guild_locale)
        if interaction.author == member:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("ban.command.callback.error.not_self", locale=interaction.guild_locale), interaction.author
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if member.bot:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("ban.command.callback.error.not_bot", locale=interaction.guild_locale), interaction.author
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if ban_time == "Never":
            try:
                await member.ban(reason=reason)
            except Forbidden:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("ban.command.callback.error.forbidden", locale=interaction.guild_locale),
                    interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except HTTPException:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("ban.command.callback.error.http", locale=interaction.guild_locale),
                    interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("ban.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "ban.command.callback.success.description.never",
                        locale=interaction.guild_locale,
                        values=(
                            member.mention, member, interaction.author.mention,
                            interaction.author, reason
                        )
                    )
                )
            )

        result = await time_converter(time=ban_time, member=interaction.author, locale=interaction.guild_locale)

        if isinstance(result, datetime):
            try:
                await member.ban(reason=reason)
            except Forbidden:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("ban.command.callback.error.forbidden", locale=interaction.guild_locale),
                    interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except HTTPException:
                embed: EmbedErrorUI = EmbedErrorUI(
                    _t.get("ban.command.callback.error.http", locale=interaction.guild_locale),
                    interaction.author
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            else:
                await self.bot.databases.moderation.add_global_ban(
                    guild=interaction.guild,
                    member=member,
                    moderator=interaction.author,
                    reason=reason,
                    unban_time=result,
                    locale=interaction.guild_locale
                )

                embed: EmbedUI = EmbedUI(
                    title=_t.get("ban.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "ban.command.callback.success.description", locale=interaction.guild_locale,
                        values=(
                            member.mention, member, interaction.author.mention,
                            interaction.author, format_dt(result), ban_time, reason
                        )
                    )
                )
                await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(embed=result, ephemeral=True)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(BanCog(bot))

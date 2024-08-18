from datetime import datetime
from typing import Literal

from asyncpg import Record
from disnake import Guild, Member, TextChannel, Message, Forbidden, Locale
from disnake.utils import format_dt

from utils.basic.helpers import EmbedErrorUI, EmbedUI
from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.handlers.moderation import time_converter
from utils.i18n import ChisatoLocalStore

PunishmentType = Literal["ban", "warn", "timeout", "kick"]
_t = ChisatoLocalStore.load("./cogs/moderation/warns.py")


class ModerationDB(Database):
    __slots__ = (
        "bot"
    )

    cluster: str = 'moderation'

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)

        self.bot = self.this_pool.client

    async def add_global_warns_settings(
            self,
            guild: Guild,
            warnings_limit: int = None,
            punishment_type: str = None,
            punishment_time: str = None
    ) -> None:
        if not await self.fetchrow("SELECT * FROM moderation_global_warns_settings WHERE guild_id = $1", guild.id):
            await self.execute(
                """
                INSERT INTO moderation_global_warns_settings (guild_id)
                VALUES ($1)
                """,
                guild.id
            )

        if warnings_limit:
            await self.execute(
                """
                UPDATE moderation_global_warns_settings
                SET warnings_limit = $1
                WHERE guild_id = $2
                """,
                warnings_limit, guild.id
            )
        if punishment_type:
            if punishment_type == 'kick':
                await self.execute(
                    """
                    UPDATE moderation_global_warns_settings
                    SET punishment_type = $1, punishment_time = '1h'
                    WHERE guild_id = $2
                    """,
                    punishment_type, guild.id
                )
            else:
                await self.execute(
                    """
                    UPDATE moderation_global_warns_settings
                    SET punishment_type = $1
                    WHERE guild_id = $2
                    """,
                    punishment_type, guild.id
                )
        if punishment_time:
            await self.execute(
                """
                UPDATE moderation_global_warns_settings
                SET punishment_time = $1
                WHERE guild_id = $2
                """,
                punishment_time, guild.id
            )

    async def get_global_warns_settings(self, guild: Guild) -> tuple:
        database_result = await self.fetchrow(
            """
            SELECT warnings_limit, punishment_type, punishment_time
            FROM moderation_global_warns_settings WHERE guild_id = $1
            """, guild.id
        ) or (3, "timeout", "1h")
        return database_result

    async def add_global_warn(
            self,
            guild: Guild,
            member: Member,
            moderator: Member,
            reason: str,
            message: Message = None,
            by_report: bool = False,
            locale: Locale = None
    ) -> EmbedErrorUI | EmbedUI:
        settings = await self.get_global_warns_settings(guild=guild)
        if locale:
            loc = locale
        else:
            loc = guild.preferred_locale

        result = await self.fetchrow(
            "SELECT MAX(warning_id) FROM moderation_global_warns WHERE guild_id = $1",
            guild.id
        )
        warning_id: int = result[0] + 1 if result[0] else 1

        await self.execute(
            """
            INSERT INTO moderation_global_warns (guild_id, member_id, moderator_id, warning_id, issue_time, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            guild.id, member.id, moderator.id, warning_id, datetime.now().timestamp(), reason
        )

        result = await self.fetchall(
            "SELECT member_id FROM moderation_global_warns WHERE guild_id = $1 AND member_id = $2",
            guild.id, member.id
        )

        description_types: dict = {
            "ban": _t.get("ban.success", locale=loc)
            if not by_report else
            f"{_t.get('ban.success', locale=loc)} {_t.get('mod.by_report', locale=loc)}",

            "warn": _t.get("warn.success", locale=loc)
            if not by_report else
            f"{_t.get('warn.success', locale=loc)} {_t.get('mod.by_report', locale=loc)}",

            "timeout": _t.get("timeout.success", locale=loc)
            if not by_report else
            f"{_t.get('timeout.success', locale=loc)} {_t.get('mod.by_report', locale=loc)}",

            "kick": _t.get("kick.success", locale=loc)
            if not by_report else
            f"{_t.get('kick.success', locale=loc)} {_t.get('mod.by_report', locale=loc)}",
        }

        if len(result) >= settings[0]:
            try:
                await self.apply_punishment(
                    member=member,
                    punishment_type=settings[1],
                    punishment_time=settings[2],
                    reason=reason,
                    locale=loc
                )
            except Forbidden:
                embed_: EmbedErrorUI = EmbedErrorUI(
                    _t.get("warn.error.add_warn.forbidden", locale=loc),
                    moderator
                )

                for row in result:
                    await self.execute(
                        "DELETE FROM moderation_global_warns WHERE guild_id = $1 AND member_id = $2",
                        guild.id, row[0]
                    )

                return embed_

            for row in result:
                await self.execute(
                    "DELETE FROM moderation_global_warns WHERE guild_id = $1 AND member_id = $2",
                    guild.id, row[0]
                )

            title_types: dict = {
                "ban": _t.get("ban.title", locale=loc),
                "timeout": _t.get("timeout.title", locale=loc),
                "kick": _t.get("kick.title", locale=loc)
            }

            embed: EmbedUI = EmbedUI(
                title=title_types[settings[1]],
                description=_t.get(
                    "warn.add_warn.success", locale=loc,
                    values=(
                        description_types[settings[1]], member.mention,
                        member, moderator.mention, moderator
                    )
                )
            )
        else:
            embed: EmbedUI = EmbedUI(
                title=_t.get("warn.title", locale=loc),
                description=_t.get(
                    "warn.add_warn.success", locale=loc,
                    values=(
                        description_types['warn'], member.mention, member.name,
                        moderator.mention, moderator.name
                    )
                )
            )

        if by_report:
            embed.description += _t.get(
                "warn.add_warn.success.part.by_report", locale=loc,
                values=(message.jump_url, message.channel)
            )

        embed.description += _t.get(
            "warn.add_warn.success.part.reason", locale=loc, values=(reason,)
        ) + _t.get(
            "warn.add_warn.success.part.amount", locale=loc, values=(len(result), settings[0])
        )

        return embed

    async def remove_global_warn(
            self, guild: Guild, moderator: Member, case_number: int, reason: str,
            locale: Locale = None
    ) -> EmbedUI:
        if result := await self.fetchrow(
                """
                SELECT member_id, moderator_id, issue_time, reason    
                FROM moderation_global_warns WHERE guild_id = $1 AND warning_id = $2
                """, guild.id, case_number
        ):
            member: Member | None = guild.get_member(result[0])
            author_warning: Member | None = guild.get_member(result[1])

            if author_warning:
                author_warning_info = _t.get(
                    "mod.with_split", locale=locale,
                    values=(author_warning.mention, author_warning.name)
                )
            else:
                author_warning_info = _t.get("mod.unknown", locale=locale)

            await self.execute(
                "DELETE FROM moderation_global_warns WHERE guild_id = $1 and warning_id = $2",
                guild.id, case_number
            )

            time: str = format_dt(result[2], style="f")

            return EmbedUI(
                title=_t.get("warn.title", locale=locale),
                description=_t.get(
                    "warn.remove_warn.success", locale=locale,
                    values=(
                        moderator.mention, moderator.name, member.mention,
                        member.name, reason, case_number, member.mention, member.name,
                        author_warning_info, result[3], time, case_number
                    )
                )
            )

    async def get_user_warns_list(self, guild: Guild, member: Member) -> list[Record]:
        return await self.fetchall(
            """
            SELECT member_id, moderator_id, warning_id, issue_time, reason    
            FROM moderation_global_warns WHERE guild_id = $1 AND member_id = $2
            """, guild.id, member.id
        )

    async def add_user_moderation_stats(
            self,
            guild: Guild,
            member: Member,
            punishment: PunishmentType,
            is_given: bool
    ) -> None:
        if not await self.fetchrow(
                "SELECT guild_id, member_id FROM moderation_stats WHERE guild_id = $1 AND member_id = $2",
                guild.id, member.id
        ):
            await self.execute(
                """
                INSERT INTO moderation_stats 
                (
                guild_id, member_id, bans_gived, warns_gived, timeouts_gived, 
                kicks_gived, bans_taked, warns_taked, timeouts_taked, kick_taked
                )
                VALUES 
                ($1, $2, 0, 0, 0, 0, 0, 0, 0, 0)
                """, guild.id, member.id
            )

        from_bool = {True: 'gived', False: 'taked'}
        await self.execute(
            f"""
            UPDATE moderation_stats 
            SET {punishment}s_{from_bool[is_given]} = {punishment}s_{from_bool[is_given]} + 1 
            WHERE guild_id = $1 AND member_id = $2
            """, guild.id, member.id
        )

    async def get_user_moderation_stats(
            self, guild: Guild, member: Member, author: Member,
            locale: Locale = None
    ) -> EmbedUI | EmbedErrorUI:
        if not (result := await self.fetchrow(
                "SELECT * FROM moderation_stats WHERE guild_id = $1 AND member_id = $2",
                guild.id, member.id
        )):
            return EmbedErrorUI(_t.get("warn.error.stats.not", locale=locale), author)
        else:
            return EmbedUI(
                title=_t.get("mod.stats.title", locale=locale),
                description=_t.get(
                    "mod.stats.embed.description", locale=locale,
                    values=tuple([result[i - 1] for i in range(len(result)) if i - 1 >= 2] + [result[-1]])
                )
            )

    async def apply_punishment(
            self,
            member: Member,
            punishment_type: str | None,
            punishment_time: str,
            reason: str,
            moderator: Member = None,
            locale: Locale = None
    ) -> None:
        if punishment_type == "timeout" or punishment_type == "ban":
            time: datetime | EmbedErrorUI = await time_converter(
                time=punishment_time, member=member, locale=locale
            )

            if punishment_type == "timeout":
                await member.timeout(reason=reason, until=time)
            else:
                try:
                    await member.ban(reason=reason)
                except Forbidden:
                    raise Forbidden
                else:
                    await self.add_global_ban(
                        guild=member.guild,
                        member=member,
                        moderator=moderator,
                        reason=reason,
                        unban_time=time
                    )
        else:
            await member.kick(reason=reason)

    async def add_global_ban(
            self,
            guild: Guild,
            member: Member,
            moderator: Member,
            reason: str,
            unban_time: datetime,
            locale: Locale = None
    ) -> EmbedErrorUI | None:
        if locale:
            loc = locale
        else:
            loc = guild.preferred_locale
        if await self.fetchrow(
                "SELECT * FROM moderation_global_bans WHERE guild_id = $1 AND member_id = $2", guild.id, member.id
        ):
            return EmbedErrorUI(_t.get("ban.error.already_banned", locale=loc), moderator)
        else:
            await self.execute(
                """
                INSERT INTO moderation_global_bans (guild_id, member_id, moderator_id, reason, unban_time)
                VALUES ($1, $2, $3, $4, $5)
                """, guild.id, member.id, moderator.id, reason, unban_time.timestamp()
            )

    async def get_guild_global_bans(
            self, current_time: datetime
    ) -> list[Record]:
        return await self.fetchall(
            "SELECT * FROM moderation_global_bans WHERE unban_time <= $1", current_time.timestamp()
        )

    async def remove_guild_on_error_global_bans(self, guild_id: int) -> None:
        await self.execute("DELETE FROM moderation_global_bans WHERE guild_id = $1", guild_id)

    async def remove_member_on_error_global_bans(self, guild_id: int, member_id: int) -> None:
        await self.execute(
            "DELETE FROM moderation_global_bans WHERE guild_id = $1 AND member_id = $2", guild_id, member_id
        )

    async def add_global_reports_settings(
            self,
            guild: Guild,
            channel: TextChannel,
    ) -> bool:
        if not await self.fetchrow(
                "SELECT * FROM moderation_global_reports_settings WHERE guild_id = $1", guild.id
        ):
            await self.execute(
                """
                INSERT INTO moderation_global_reports_settings (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                guild.id, channel.id
            )
            return True
        else:
            await self.execute(
                """
                UPDATE moderation_global_reports_settings
                SET channel_id = $1
                WHERE guild_id = $2
                """,
                channel.id, guild.id,
            )
            return False

    async def remove_global_reports_settings(
            self,
            guild: Guild
    ) -> bool:
        if await self.fetchrow(
                "SELECT * FROM moderation_global_reports_settings WHERE guild_id = $1", guild.id
        ):
            await self.execute('DELETE FROM moderation_global_reports_settings WHERE guild_id = $1', guild.id)
            return True

        return False

    async def get_global_reports_settings(
            self,
            guild: Guild,
    ) -> int | None:
        result = await self.fetchrow("SELECT * FROM moderation_global_reports_settings WHERE guild_id = $1", guild.id)
        return result[1] if result else None

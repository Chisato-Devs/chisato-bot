from typing import TYPE_CHECKING, List, Sequence, Dict, Type

from asyncpg import Record
from disnake import (
    AutoModActionExecution,
    AutoModRule,
    Message,
    Thread,
    Guild,
    Emoji,
    Role,
    GuildScheduledEvent,
    Member,
    User,
    GuildSticker,
    Invite,
    Reaction,
    ThreadMember,
    VoiceState,
    TextChannel,
    Forbidden,
    HTTPException,
    NotFound,
    AuditLogAction,
    VoiceChannel,
    CategoryChannel,
    StageChannel,
    ForumChannel,
    AuditLogEntry,
    GuildScheduledEventEntityType,
    ContentFilter
)
from disnake.abc import GuildChannel
from disnake.utils import format_dt

from utils.basic import CogUI, EmbedUI, EmbedErrorUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t: ChisatoLocalStore = ChisatoLocalStore.load(__file__)


class LoggingCog(CogUI):

    @CogUI.listener()
    async def on_automod_action_execution(self, execution: AutoModActionExecution) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=execution.guild)
            channel_send: TextChannel | None = execution.guild.get_channel(settings[5])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        try:
            rule: AutoModRule = await execution.guild.fetch_automod_rule(execution.rule_id)
        except (Forbidden, NotFound, HTTPException) as error:
            error_messages: Dict[Type[Forbidden | NotFound | HTTPException], str] = {
                Forbidden: _t.get(
                    key="logging.on_automod_action_execution.forbidden",
                    locale=execution.guild.preferred_locale
                ),
                NotFound: _t.get(
                    key="logging.on_automod_action_execution.notfound",
                    locale=execution.guild.preferred_locale
                ),
                HTTPException: _t.get(
                    key="logging.on_automod_action_execution.httpexception",
                    locale=execution.guild.preferred_locale
                ),
            }

            embed: EmbedErrorUI = EmbedErrorUI(error_messages[type(error)], member=execution.guild.owner)
            await channel_send.send(embed=embed)
        else:
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.automod", locale=execution.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_automod_action_execution.embed.description",
                    locale=execution.guild.preferred_locale,
                    values=(
                        execution.user.mention,
                        execution.user,
                        execution.channel.mention,
                        execution.channel,
                        rule.name,
                        execution.content,
                        execution.matched_keyword
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

    @CogUI.listener()
    async def on_automod_rule_create(self, rule: AutoModRule) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=rule.guild)
            channel_send: TextChannel | None = rule.guild.get_channel(settings[5])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=rule.guild.preferred_locale)
        allowed_roles_list: List[str] | str = [role.mention for role in rule.exempt_roles] or not_ind
        allowed_channels_list: List[str] | str = [channel.mention for channel in rule.exempt_channels] or not_ind

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.title.automod", locale=rule.guild.preferred_locale),
            description=_t.get(
                key="logging.on_automod_rule_create.embed.description",
                locale=rule.guild.preferred_locale,
                values=(
                    rule.creator.mention,
                    rule.creator,
                    rule.name,
                    rule.trigger_metadata.keyword_filter or not_ind,
                    rule.trigger_metadata.allow_list or not_ind,
                    rule.trigger_metadata.regex_patterns or not_ind,
                    allowed_roles_list,
                    allowed_channels_list,
                    rule.enabled
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_automod_rule_delete(self, rule: AutoModRule) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=rule.guild)
            channel_send: TextChannel | None = rule.guild.get_channel(settings[5])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=rule.guild.preferred_locale)
        allowed_roles_list: List[str] | str = [role.mention for role in rule.exempt_roles] or not_ind
        allowed_channels_list: List[str] | str = [channel.mention for channel in rule.exempt_channels] or not_ind

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.not_indicated", locale=rule.guild.preferred_locale),
            description=_t.get(
                key="logging.on_automod_rule_delete.embed.description",
                locale=rule.guild.preferred_locale,
                values=(
                    rule.creator.mention,
                    rule.creator,
                    rule.name,
                    rule.trigger_metadata.keyword_filter or not_ind,
                    rule.trigger_metadata.allow_list or not_ind,
                    rule.trigger_metadata.regex_patterns or not_ind,
                    allowed_roles_list,
                    allowed_channels_list,
                    rule.enabled
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_channel_create(self, channel: GuildChannel) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=channel.guild)
            channel_send: TextChannel | None = channel.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=channel.guild.preferred_locale)
        creator = await channel.guild.audit_logs(
            limit=1,
            action=AuditLogAction.channel_create
        ).flatten()

        if isinstance(channel, TextChannel):
            duration: Dict[int, str] = {
                60: "1h",
                1440: "1d",
                4320: "3d",
                10080: "1w"
            }

            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_create", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_create.embed.description",
                    locale=channel.guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.is_news(),
                        channel.position,
                        channel.nsfw,
                        channel.slowmode_delay,
                        duration[channel.default_auto_archive_duration]
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, VoiceChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_create", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_create.embed.description2",
                    locale=channel.guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.user_limit,
                        channel.bitrate,
                        channel.nsfw,
                        channel.rtc_region,
                        channel.video_quality_mode,
                        channel.slowmode_delay
                    )
                )
            )
            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, CategoryChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.category_create", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_create.embed.description3",
                    locale=channel.guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        channel.name,
                        channel.position,
                        channel.nsfw
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, StageChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_create", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_create.embed.description4",
                    locale=channel.guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.position,
                        channel.bitrate,
                        channel.nsfw,
                        channel.rtc_region,
                        channel.user_limit,
                        channel.video_quality_mode,
                        channel.slowmode_delay
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, ForumChannel):
            duration: Dict[int, str] = {
                60: "1h",
                1440: "1d",
                4320: "3d",
                10080: "1w"
            }

            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_create", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_create.embed.description5",
                    locale=channel.guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.position,
                        channel.nsfw,
                        duration[channel.default_auto_archive_duration],
                        channel.slowmode_delay,
                        channel.default_thread_slowmode_delay,
                        channel.default_sort_order,
                        channel.default_layout
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

    @CogUI.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=channel.guild)
            channel_send: TextChannel | None = channel.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=channel.guild.preferred_locale)
        deleter = await channel.guild.audit_logs(
            limit=1,
            action=AuditLogAction.channel_delete
        ).flatten()

        if isinstance(channel, TextChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_delete", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_delete.embed.description",
                    locale=channel.guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.is_news(),
                        channel.position,
                        channel.nsfw
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, VoiceChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_delete", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_delete.embed.description2",
                    locale=channel.guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.user_limit,
                        channel.bitrate,
                        channel.nsfw,
                        channel.rtc_region,
                        channel.video_quality_mode,
                        channel.slowmode_delay
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, CategoryChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.category_delete", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_delete.embed.description3",
                    locale=channel.guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        channel.name,
                        channel.position,
                        channel.nsfw
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, StageChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_delete", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_delete.embed.description4",
                    locale=channel.guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.position,
                        channel.bitrate,
                        channel.nsfw,
                        channel.rtc_region,
                        channel.user_limit,
                        channel.video_quality_mode,
                        channel.slowmode_delay
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(channel, ForumChannel):
            duration: Dict[int, str] = {
                60: "1h",
                1440: "1d",
                4320: "3d",
                10080: "1w"
            }

            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_delete", locale=channel.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_delete.embed.description5",
                    locale=channel.guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        channel.jump_url,
                        channel.name,
                        channel.category or not_ind,
                        channel.topic or not_ind,
                        channel.position,
                        channel.nsfw,
                        duration[channel.default_auto_archive_duration],
                        channel.slowmode_delay,
                        channel.default_thread_slowmode_delay,
                        channel.default_sort_order,
                        channel.default_layout
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

    @CogUI.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=after.guild.preferred_locale)
        updater = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.channel_update
        ).flatten()

        if isinstance(before, TextChannel) and isinstance(after, TextChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_update", locale=after.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_update.embed.description",
                    locale=after.guild.preferred_locale,
                    values=(
                        updater[0].user.mention if updater else "Unknown",
                        updater[0].user if updater else "Unknown",
                        after.jump_url,
                        after.name
                    )
                )
            )

            if before.name != after.name:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.name",
                    locale=after.guild.preferred_locale,
                    values=(before.name, after.name)
                )

            if before.category != after.category:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.category",
                    locale=after.guild.preferred_locale,
                    values=(before.category or not_ind, after.category or not_ind)
                )

            if before.topic != after.topic:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.topic",
                    locale=after.guild.preferred_locale,
                    values=(
                        before.topic if before.topic else "None", after.topic if after.topic else "None"
                    )
                )

            if before.is_news() != after.is_news():
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.is_news",
                    locale=after.guild.preferred_locale,
                    values=(before.is_news(), after.is_news())
                )

            if before.position != after.position:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.position",
                    locale=after.guild.preferred_locale,
                    values=(before.position, after.position)
                )

            if before.nsfw != after.nsfw:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.text_channel.nsfw",
                    locale=after.guild.preferred_locale,
                    values=(before.nsfw, after.nsfw)
                )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(before, VoiceChannel) and isinstance(after, VoiceChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_update", locale=after.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_update.embed.description2",
                    locale=after.guild.preferred_locale,
                    values=(
                        updater[0].user.mention if updater else "Unknown",
                        updater[0].user if updater else "Unknown",
                        after.jump_url,
                        after.name
                    )
                )
            )

            if before.name != after.name:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.name",
                    locale=after.guild.preferred_locale,
                    values=(before.name, after.name)
                )

            if before.category != after.category:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.category",
                    locale=after.guild.preferred_locale,
                    values=(before.category or not_ind, after.category or not_ind)
                )

            if before.user_limit != after.user_limit:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.user_limit",
                    locale=after.guild.preferred_locale,
                    values=(before.user_limit, after.user_limit)
                )

            if before.bitrate != after.bitrate:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.bitrate",
                    locale=after.guild.preferred_locale,
                    values=(before.bitrate, after.bitrate)
                )

            if before.nsfw != after.nsfw:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.nsfw",
                    locale=after.guild.preferred_locale,
                    values=(before.nsfw, after.nsfw)
                )

            if before.rtc_region != after.rtc_region:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.rtc_region",
                    locale=after.guild.preferred_locale,
                    values=(before.rtc_region, after.rtc_region)
                )

            if before.video_quality_mode != after.video_quality_mode:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.video_quality_mode",
                    locale=after.guild.preferred_locale,
                    values=(before.video_quality_mode, after.video_quality_mode)
                )

            if before.slowmode_delay != after.slowmode_delay:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.voice_channel.slowmode_delay",
                    locale=after.guild.preferred_locale,
                    values=(before.slowmode_delay, after.slowmode_delay)
                )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(before, CategoryChannel) and isinstance(after, CategoryChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.category_update", locale=after.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_update.embed.description3",
                    locale=after.guild.preferred_locale,
                    values=(
                        updater[0].user.mention,
                        updater[0].user,
                        before.category or not_ind,
                        after.category or not_ind
                    )
                )
            )

            if before.name != after.name:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.category_channel.name",
                    locale=after.guild.preferred_locale,
                    values=(before.name, after.name)
                )

            if before.position != after.position:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.category_channel.position",
                    locale=after.guild.preferred_locale,
                    values=(before.position, after.position)
                )

            if before.nsfw != after.nsfw:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.category_channel.nsfw",
                    locale=after.guild.preferred_locale,
                    values=(before.nsfw, after.nsfw)
                )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(before, StageChannel) and isinstance(after, StageChannel):
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_update", locale=after.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_update.embed.description4",
                    locale=after.guild.preferred_locale,
                    values=(updater[0].user.mention, updater[0].user, after.jump_url, after.name)
                )
            )

            if before.name != after.name:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.name",
                    locale=after.guild.preferred_locale,
                    values=(before.name, after.name)
                )

            if before.category != after.category:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.category",
                    locale=after.guild.preferred_locale,
                    values=(before.category or not_ind, after.category or not_ind)
                )

            if before.topic != after.topic:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.topic",
                    locale=after.guild.preferred_locale,
                    values=(before.topic or not_ind, after.topic or not_ind)
                )

            if before.position != after.position:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.position",
                    locale=after.guild.preferred_locale,
                    values=(before.position, after.position)
                )

            if before.bitrate != after.bitrate:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.bitrate",
                    locale=after.guild.preferred_locale,
                    values=(before.bitrate, after.bitrate)
                )

            if before.nsfw != after.nsfw:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.nsfw",
                    locale=after.guild.preferred_locale,
                    values=(before.nsfw, after.nsfw)
                )

            if before.rtc_region != after.rtc_region:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.rtc_region",
                    locale=after.guild.preferred_locale,
                    values=(before.rtc_region, after.rtc_region)
                )

            if before.user_limit != after.user_limit:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.user_limit",
                    locale=after.guild.preferred_locale,
                    values=(before.user_limit, after.user_limit)
                )

            if before.video_quality_mode != after.video_quality_mode:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.video_quality_mode",
                    locale=after.guild.preferred_locale,
                    values=(before.video_quality_mode, after.video_quality_mode)
                )

            if before.slowmode_delay != after.slowmode_delay:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.stage_channel.slowmode_delay",
                    locale=after.guild.preferred_locale,
                    values=(before.slowmode_delay, after.slowmode_delay)
                )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

        elif isinstance(before, ForumChannel) and isinstance(after, ForumChannel):
            duration: Dict[int, str] = {
                60: "1h",
                1440: "1d",
                4320: "3d",
                10080: "1w"
            }

            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.title.channel_update", locale=after.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_guild_channel_update.embed.description5",
                    locale=after.guild.preferred_locale,
                    values=(updater[0].user.mention, updater[0].user, after.jump_url, after.name)
                )
            )

            if before.category != after.category:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.category",
                    locale=after.guild.preferred_locale,
                    values=(before.category or not_ind, after.category or not_ind)
                )

            if before.topic != after.topic:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.topic",
                    locale=after.guild.preferred_locale,
                    values=(before.topic or not_ind, after.topic or not_ind)
                )

            if before.position != after.position:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.position",
                    locale=after.guild.preferred_locale,
                    values=(before.position, after.position)
                )

            if before.nsfw != after.nsfw:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.nsfw",
                    locale=after.guild.preferred_locale,
                    values=(before.nsfw, after.nsfw)
                )

            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.default_auto_archive_duration",
                    locale=after.guild.preferred_locale,
                    values=(
                        duration[before.default_auto_archive_duration], duration[after.default_auto_archive_duration]
                    )
                )

            if before.slowmode_delay != after.slowmode_delay:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.slowmode_delay",
                    locale=after.guild.preferred_locale,
                    values=(before.slowmode_delay, after.slowmode_delay)
                )

            if before.default_thread_slowmode_delay != after.default_thread_slowmode_delay:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.default_thread_slowmode_delay",
                    locale=after.guild.preferred_locale,
                    values=(before.default_thread_slowmode_delay, after.default_thread_slowmode_delay)
                )

            if before.default_sort_order != after.default_sort_order:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.default_sort_order",
                    locale=after.guild.preferred_locale,
                    values=(before.default_sort_order, after.default_sort_order)
                )

            if before.default_layout != after.default_layout:
                embed.description += _t.get(
                    key="logging.on_guild_channel_update.forum_channel.default_layout",
                    locale=after.guild.preferred_locale,
                    values=(before.default_layout, after.default_layout)
                )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass

    @CogUI.listener()
    async def on_guild_channel_pins_update(self, channel: GuildChannel | Thread, _) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=channel.guild)
            channel_send: TextChannel | None = channel.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        piner_unpiner: List[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_guild_channel_pins_update.title", locale=channel.guild.preferred_locale),
            description=""
        )

        match piner_unpiner[0].action:
            case AuditLogAction.message_pin:
                embed.description += _t.get(
                    key="logging.on_guild_channel_pins_update.message_pin",
                    locale=channel.guild.preferred_locale,
                    values=(piner_unpiner[0].user.mention, piner_unpiner[0].user, channel.jump_url, channel.name)
                )
            case AuditLogAction.message_unpin:
                embed.description += _t.get(
                    key="logging.on_guild_channel_pins_update.message_unpin",
                    locale=channel.guild.preferred_locale,
                    values=(piner_unpiner[0].user.mention, piner_unpiner[0].user, channel.jump_url, channel.name)
                )
            case _:  # :D
                return

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_emojis_update(self, guild: Guild, before: Sequence[Emoji], after: Sequence[Emoji]) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=guild)
            channel_send: TextChannel | None = guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_guild_emojis_update.title", locale=guild.preferred_locale),
            description=""
        )

        if len(before) > len(after):
            deleter: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.emoji_delete
            ).flatten()

            deleted_emojis: set[Emoji] = set(before) - set(after)
            deleted_emojis_str: str = ", ".join([str(emoji) for emoji in deleted_emojis])

            embed.description += _t.get(
                key="logging.on_guild_emojis_update.removed",
                locale=guild.preferred_locale,
                values=(deleter[0].user.mention, deleter[0].user, deleted_emojis_str)
            )

        elif len(before) < len(after):
            creator: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.emoji_create
            ).flatten()

            created_emojis: set[Emoji] = set(after) - set(before)
            created_emojis_str: str = ", ".join([str(emoji) for emoji in created_emojis])

            embed.description += _t.get(
                key="logging.on_guild_emojis_update.added",
                locale=guild.preferred_locale,
                values=(creator[0].user.mention, creator[0].user, created_emojis_str, created_emojis_str)
            )

        elif len(before) == len(after):
            updater: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.emoji_update
            ).flatten()

            embed.description += _t.get(
                key="logging.on_guild_emojis_update.changed",
                locale=guild.preferred_locale,
                values=(updater[0].user.mention, updater[0].user)
            )

            for before_emoji, after_emoji in zip(before, after):
                if before_emoji.name != after_emoji.name:
                    embed.description += _t.get(
                        key="logging.on_guild_emojis_update.changed.name",
                        locale=guild.preferred_locale,
                        values=(before_emoji, before_emoji.name, after_emoji, after_emoji.name)
                    )

        else:
            return

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_role_create(self, role: Role) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=role.guild)
            channel_send: TextChannel | None = role.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        creator: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.role_create
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_guild_role.title", locale=role.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_role_create.embed.description",
                locale=role.guild.preferred_locale,
                values=(creator[0].user.mention, creator[0].user, role.mention, role.name)
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_role_delete(self, role: Role) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=role.guild)
            channel_send: TextChannel | None = role.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        deleter: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.role_delete
        ).flatten()

        role_emoji_info: str = _t.get(key="logging.not_indicated", locale=role.guild.preferred_locale)
        role_icon_info: str = _t.get(key="logging.not_indicated", locale=role.guild.preferred_locale)

        if role.emoji:
            role_emoji_info: str = _t.get(
                key="logging.on_guild_role_delete.role_emoji",
                locale=role.guild.preferred_locale,
                values=(role.emoji, role.emoji.name)
            )

        if role.icon:
            role_icon_info: str = f"[link]({role.emoji.url})"

        permission_list: List[str] = []
        permissions_formatted: Dict[str, str] = _t.get(
            key="logging.permissions",
            locale=role.guild.preferred_locale
        )

        for permission, value in role.permissions:
            if value:
                translated_permission: str = permissions_formatted.get(permission, permission)
                permission_list.append(translated_permission)

        permission_string: str = ", ".join(permission_list)

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_guild_role.title", locale=role.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_role_delete.embed.description",
                locale=role.guild.preferred_locale,
                values=(
                    deleter[0].user.mention,
                    deleter[0].user,
                    role.name,
                    role.color,
                    role.position,
                    role_emoji_info,
                    role_icon_info,
                    role.managed,
                    role.mentionable,
                    len(role.members),
                    role.hoist,
                    permission_string
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_role_update(self, before: Role, after: Role) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        if before.position != after.position:
            return

        updater: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.role_update
        ).flatten()

        not_ind: str = _t.get(key="logging.not_indicated", locale=before.guild.preferred_locale)

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_guild_role.title", locale=before.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_role_update.embed.description",
                locale=before.guild.preferred_locale,
                values=(
                    updater[0].user.mention,
                    updater[0].user,
                    after.mention,
                    after.name
                )
            )
        )

        if before.name != after.name:
            embed.description += _t.get(
                key="logging.on_guild_role_update.name",
                locale=before.guild.preferred_locale,
                values=(
                    before.name,
                    after.name
                )
            )

        if before.color != after.color:
            embed.description += _t.get(
                key="logging.on_guild_role_update.color",
                locale=before.guild.preferred_locale,
                values=(
                    before.color,
                    after.color
                )
            )

        if before.emoji != after.emoji:
            if before.emoji is None and after.emoji is not None:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.emoji_added",
                    locale=before.guild.preferred_locale,
                    values=(not_ind, after.emoji, after.emoji.name)
                )
            elif before.emoji is not None and after.emoji is None:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.emoji_removed",
                    locale=before.guild.preferred_locale,
                    values=(before.emoji, before.emoji.name, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.emoji_changed",
                    locale=before.guild.preferred_locale,
                    values=(before.emoji, before.emoji.name, after.emoji, after.emoji.name)
                )

        if before.icon != after.icon:
            if before.icon is None and after.icon is not None:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.icon_added",
                    locale=before.guild.preferred_locale,
                    values=(not_ind, after.icon.url)
                )
            elif before.icon is not None and after.icon is None:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.icon_removed",
                    locale=before.guild.preferred_locale,
                    values=(before.icon.url, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_role_update.icon_changed",
                    locale=before.guild.preferred_locale,
                    values=(before.icon.url, after.icon.url)
                )

        if before.managed != after.managed:
            embed.description += _t.get(
                key="logging.on_guild_role_update.managed",
                locale=before.guild.preferred_locale,
                values=(before.managed, after.managed)
            )

        if before.mentionable != after.mentionable:
            embed.description += _t.get(
                key="logging.on_guild_role_update.mentionable",
                locale=before.guild.preferred_locale,
                values=(before.mentionable, after.mentionable)
            )

        if before.hoist != after.hoist:
            embed.description += _t.get(
                key="logging.on_guild_role_update.hoist",
                locale=before.guild.preferred_locale,
                values=(before.hoist, after.hoist)
            )

        if before.permissions != after.permissions:
            permissions_formatted: Dict[str, str] = _t.get(
                key="logging.permissions",
                locale=before.guild.preferred_locale
            )

            added_changes: List[str] = []
            removed_changes: List[str] = []
            for perm, value in after.permissions:
                if getattr(after.permissions, perm) != getattr(before.permissions, perm):
                    if perm in permissions_formatted:
                        change: str = permissions_formatted[perm]
                    else:
                        change: str = perm
                    if value:
                        added_changes.append(change)
                    else:
                        removed_changes.append(change)

            if added_changes or removed_changes:
                if added_changes:
                    added_changes_string: str = ", ".join(added_changes)

                    embed.description += _t.get(
                        key="logging.on_guild_role_update.permissions_added",
                        locale=before.guild.preferred_locale,
                        values=(added_changes_string,)
                    )

                if removed_changes:
                    removed_changes_string: str = ", ".join(removed_changes)

                    embed.description += _t.get(
                        key="logging.on_guild_role_update.permissions_removed",
                        locale=before.guild.preferred_locale,
                        values=(removed_changes_string,)
                    )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_scheduled_event_create(self, event: GuildScheduledEvent) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=event.guild)
            channel_send: TextChannel | None = event.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=event.guild.preferred_locale)

        if event.entity_type == GuildScheduledEventEntityType.external:
            place_info: str = f"`{event.entity_metadata.location}`"
        else:
            place_info: str = _t.get(
                key="logging.on_guild_scheduled_event_delete.place_info",
                locale=event.guild.preferred_locale,
                values=(event.channel.mention, event.channel.name)
            )

        if event.image:
            image_info: str = f"[link]({event.image.url})"
        else:
            image_info: str = f"`{not_ind}`"

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.scheduled_event.title", locale=event.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_scheduled_event_create.embed.description",
                locale=event.guild.preferred_locale,
                values=(
                    event.creator.mention,
                    event.creator,
                    place_info,
                    event.name,
                    event.description or not_ind,
                    format_dt(event.scheduled_start_time),
                    format_dt(event.scheduled_end_time),
                    image_info
                )
            )
        )
        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_scheduled_event_delete(self, event: GuildScheduledEvent) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=event.guild)
            channel_send: TextChannel | None = event.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        deleter: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.guild_scheduled_event_delete
        ).flatten()

        not_ind: str = _t.get(key="logging.not_indicated", locale=event.guild.preferred_locale)

        if event.entity_type == GuildScheduledEventEntityType.external:
            place_info: str = f"`{event.entity_metadata.location}`"
        else:
            place_info: str = _t.get(
                key="logging.on_guild_scheduled_event_delete.place_info",
                locale=event.guild.preferred_locale,
                values=(event.channel.mention, event.channel.name)
            )

        if event.image:
            image_info: str = f"[link]({event.image.url})"
        else:
            image_info: str = f"`{not_ind}`"

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.scheduled_event.title", locale=event.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_scheduled_event_delete.embed.description",
                locale=event.guild.preferred_locale,
                values=(
                    deleter[0].user.mention,
                    deleter[0].user,
                    place_info,
                    event.name,
                    event.description or not_ind,
                    format_dt(event.scheduled_start_time),
                    format_dt(event.scheduled_end_time),
                    image_info
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_scheduled_event_update(self, before: GuildScheduledEvent, after: GuildScheduledEvent) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        updater: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.guild_scheduled_event_update
        ).flatten()

        not_ind: str = _t.get(key="logging.not_indicated", locale=before.guild.preferred_locale)

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.scheduled_event.title", locale=before.guild.preferred_locale),
            description=_t.get(
                key="logging.on_guild_scheduled_event_update.embed.description",
                locale=before.guild.preferred_locale,
                values=(
                    updater[0].user.mention,
                    updater[0].user
                )
            )
        )

        if before.entity_type != after.entity_type:
            if (before.entity_type == GuildScheduledEventEntityType.external
                    and after.entity_type != GuildScheduledEventEntityType.external):
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.entity_type_1",
                    locale=before.guild.preferred_locale,
                    values=(before.entity_metadata.location, after.channel.mention, after.channel.name)
                )

            elif (before.entity_type != GuildScheduledEventEntityType.external
                  and after.entity_type == GuildScheduledEventEntityType.external):
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.entity_type_2",
                    locale=before.guild.preferred_locale,
                    values=(before.channel.mention, before.channel.name, after.entity_metadata.location)
                )

            else:
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.entity_type_3",
                    locale=before.guild.preferred_locale,
                    values=(before.channel.mention, before.channel.name, after.channel.mention, after.channel.name)
                )

        if before.name != after.name:
            embed.description += _t.get(
                key="logging.on_guild_scheduled_event_update.name_change",
                locale=before.guild.preferred_locale,
                values=(before.name, after.name)
            )

        if before.description != after.description:
            embed.description += _t.get(
                key="logging.on_guild_scheduled_event_update.description_change",
                locale=before.guild.preferred_locale,
                values=(before.description or not_ind, after.description or not_ind)
            )

        if before.scheduled_start_time != after.scheduled_start_time:
            embed.description += _t.get(
                key="logging.on_guild_scheduled_event_update.start_time_change",
                locale=before.guild.preferred_locale,
                values=(
                    format_dt(before.scheduled_start_time),
                    format_dt(after.scheduled_start_time)
                )
            )

        if before.scheduled_end_time != after.scheduled_end_time:
            embed.description += _t.get(
                key="logging.on_guild_scheduled_event_update.end_time_change",
                locale=before.guild.preferred_locale,
                values=(
                    format_dt(before.scheduled_end_time),
                    format_dt(after.scheduled_end_time)
                )
            )

        if before.image != after.image:
            if before.image is None and after.image is not None:
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.image_added",
                    locale=updater[0].guild.preferred_locale,
                    values=(not_ind, after.image.url)
                )
            elif before.image is not None and after.image is None:
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.image_removed",
                    locale=updater[0].guild.preferred_locale,
                    values=(before.image.url, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_scheduled_event_update.image_changed",
                    locale=updater[0].guild.preferred_locale,
                    values=(before.image.url, after.image.url)
                )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_stickers_update(
            self,
            guild: Guild,
            before: Sequence[GuildSticker],
            after: Sequence[GuildSticker]
    ) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=guild)
            channel_send: TextChannel | None = guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.stickers_update.title", locale=guild.preferred_locale),
            description=""
        )

        not_ind: str = _t.get(key="logging.not_indicated", locale=guild.preferred_locale)

        if len(before) > len(after):
            deleter: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.sticker_delete
            ).flatten()

            deleted_sticker: set[GuildSticker] = set(before) - set(after)

            for sticker in deleted_sticker:
                embed.description += _t.get(
                    key="logging.on_guild_stickers_update.sticker_deleted",
                    locale=guild.preferred_locale,
                    values=(
                        deleter[0].user.mention,
                        deleter[0].user,
                        sticker.name,
                        sticker.description if sticker.description else not_ind,
                        sticker.emoji
                    )
                )

        elif len(before) < len(after):
            creator: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.sticker_create
            ).flatten()

            created_sticker: set[GuildSticker] = set(after) - set(before)

            for sticker in created_sticker:
                embed.description += _t.get(
                    key="logging.on_guild_stickers_update.sticker_created",
                    locale=guild.preferred_locale,
                    values=(
                        creator[0].user.mention,
                        creator[0].user,
                        sticker.name,
                        sticker.description if sticker.description else not_ind,
                        sticker.emoji
                    )
                )

        elif len(before) == len(after):
            updater: list[AuditLogEntry] = await guild.audit_logs(
                limit=1,
                action=AuditLogAction.sticker_update
            ).flatten()

            embed.description += _t.get(
                key="logging.on_guild_stickers_update.sticker_updated",
                locale=guild.preferred_locale,
                values=(updater[0].user.mention, updater[0].user)
            )

            for before_sticker, after_sticker in zip(before, after):
                if before_sticker.name != after_sticker.name:
                    embed.description += _t.get(
                        key="logging.on_guild_stickers_update.sticker_name_change",
                        locale=guild.preferred_locale,
                        values=(before_sticker.name, after_sticker.name)
                    )

                if before_sticker.description != after_sticker.description:
                    embed.description += _t.get(
                        key="logging.on_guild_stickers_update.sticker_description_change",
                        locale=guild.preferred_locale,
                        values=(before_sticker.description, after_sticker.description)
                    )

                if before_sticker.emoji != after_sticker.emoji:
                    embed.description += _t.get(
                        key="logging.on_guild_stickers_update.sticker_emoji_change",
                        locale=guild.preferred_locale,
                        values=(before_sticker.emoji, after_sticker.emoji)
                    )
        else:
            return

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_guild_update(self, before: Guild, after: Guild) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before)
            channel_send: TextChannel | None = before.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        if before.widget_enabled != after.widget_enabled:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.guild_update.title", locale=after.preferred_locale),
            description=_t.get(key="logging.on_guild_update.embed.description", locale=after.preferred_locale)
        )

        not_ind: str = _t.get(key="logging.not_indicated", locale=after.preferred_locale)

        if before.name != after.name:
            embed.description += _t.get(
                key="logging.on_guild_update.name",
                locale=after.preferred_locale,
                values=(before.name, after.name)
            )

        if before.description != after.description:
            embed.description += _t.get(
                key="logging.on_guild_update.description",
                locale=after.preferred_locale,
                values=(before.description, after.description)
            )

        if before.icon != after.icon:
            if before.icon is None and after.icon is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.icon_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.icon.url)
                )
            elif before.icon is not None and after.icon is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.icon_removed",
                    locale=after.preferred_locale,
                    values=(before.icon.url, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.icon_changed",
                    locale=after.preferred_locale,
                    values=(before.icon.url, after.icon.url)
                )

        if before.banner != after.banner:
            if before.banner is None and after.banner is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.banner_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.banner.url)
                )
            elif before.banner is not None and after.banner is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.banner_removed",
                    locale=after.preferred_locale,
                    values=(before.banner.url, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.banner_changed",
                    locale=after.preferred_locale,
                    values=(before.banner.url, after.banner.url)
                )

        if before.afk_channel != after.afk_channel:
            if not before.afk_channel and after.afk_channel:
                embed.description += _t.get(
                    key="logging.on_guild_update.afk_channel_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.afk_channel.mention, after.afk_channel.name)
                )
            elif not after.afk_channel and before.afk_channel:
                embed.description += _t.get(
                    key="logging.on_guild_update.afk_channel_removed",
                    locale=after.preferred_locale,
                    values=(before.afk_channel.mention, before.afk_channel.name, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.afk_channel_changed",
                    locale=after.preferred_locale,
                    values=(
                        before.afk_channel.mention,
                        before.afk_channel.name,
                        after.afk_channel.mention,
                        after.afk_channel.name
                    )
                )

        if before.afk_timeout != after.afk_timeout:
            afk_timeout_converter: Dict = {
                60: "1m",
                300: "5m",
                900: "15m",
                1800: "30m",
                3600: "1h"
            }

            embed.description += _t.get(
                key="logging.on_guild_update.afk_timeout_changed",
                locale=after.preferred_locale,
                values=(afk_timeout_converter[before.afk_timeout], afk_timeout_converter[after.afk_timeout])
            )

        if before.bitrate_limit != after.bitrate_limit:
            embed.description += _t.get(
                key="logging.on_guild_update.bitrate_limit_changed",
                locale=after.preferred_locale,
                values=(int(before.bitrate_limit), int(after.bitrate_limit))
            )

        if before.default_notifications != after.default_notifications:
            default_notifications_converter = {
                "logging.on_guild_update.default_notifications.all_messages": _t.get(
                    key="logging.on_guild_update.default_notifications.all_messages",
                    locale=after.preferred_locale
                ),
                "logging.on_guild_update.default_notifications.only_mentions": _t.get(
                    key="logging.on_guild_update.default_notifications.only_mentions",
                    locale=after.preferred_locale
                )
            }

            embed.description += _t.get(
                key="logging.on_guild_update.default_notifications_changed",
                locale=after.preferred_locale,
                values=(
                    default_notifications_converter[str(before.default_notifications)],
                    default_notifications_converter[str(after.default_notifications)]
                )
            )

        if before.explicit_content_filter != after.explicit_content_filter:
            explicit_content_filter_converter: Dict = {
                ContentFilter.all_members: _t.get(
                    key="logging.on_guild_update.content_filter.all_members",
                    locale=after.preferred_locale
                ),
                ContentFilter.no_role: _t.get(
                    key="logging.on_guild_update.content_filter.no_role",
                    locale=after.preferred_locale
                ),
                ContentFilter.disabled: _t.get(
                    key="logging.on_guild_update.content_filter.disabled",
                    locale=after.preferred_locale
                )
            }

            embed.description += _t.get(
                key="logging.on_guild_update.explicit_content_filter_changed",
                locale=after.preferred_locale,
                values=(
                    explicit_content_filter_converter[before.explicit_content_filter],
                    explicit_content_filter_converter[after.explicit_content_filter]
                )
            )

        if before.mfa_level != after.mfa_level:
            mfa_level_converter: Dict = {
                0: True,
                1: False
            }

            embed.description += _t.get(
                key="logging.on_guild_update.mfa_level_changed",
                locale=after.preferred_locale,
                values=(
                    mfa_level_converter[before.mfa_level],
                    mfa_level_converter[after.mfa_level]
                )
            )

        if before.owner != after.owner:
            embed.description += _t.get(
                key="logging.on_guild_update.owner_changed",
                locale=after.preferred_locale,
                values=(
                    before.owner.mention,
                    before.owner,
                    after.owner.mention,
                    after.owner
                )
            )

        if before.preferred_locale != after.preferred_locale:
            embed.description += _t.get(
                key="logging.on_guild_update.preferred_locale_changed",
                locale=after.preferred_locale,
                values=(before.preferred_locale, after.preferred_locale)
            )

        if before.premium_progress_bar_enabled != after.premium_progress_bar_enabled:
            embed.description += _t.get(
                key="logging.on_guild_update.premium_progress_bar_enabled_changed",
                locale=after.preferred_locale,
                values=(before.premium_progress_bar_enabled, after.premium_progress_bar_enabled)
            )

        if before.premium_subscriber_role != after.premium_subscriber_role:
            embed.description += _t.get(
                key="logging.on_guild_update.premium_subscriber_role_changed",
                locale=after.preferred_locale,
                values=(
                    before.premium_subscriber_role.mention,
                    before.premium_subscriber_role.name,
                    after.premium_subscriber_role.mention,
                    after.premium_subscriber_role.name
                )
            )

        if before.premium_subscription_count != after.premium_subscription_count:
            embed.description += _t.get(
                key="logging.on_guild_update.premium_subscription_count_changed",
                locale=after.preferred_locale,
                values=(before.premium_subscription_count, after.premium_subscription_count)
            )

        if before.public_updates_channel != after.public_updates_channel:
            if before.public_updates_channel is None and after.public_updates_channel is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.public_updates_channel_added",
                    locale=after.preferred_locale,
                    values=(
                        not_ind,
                        after.public_updates_channel.mention,
                        after.public_updates_channel.name
                    )
                )

            elif before.public_updates_channel is not None and after.public_updates_channel is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.public_updates_channel_removed",
                    locale=after.preferred_locale,
                    values=(
                        before.public_updates_channel.mention,
                        before.public_updates_channel.name,
                        not_ind
                    )
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.public_updates_channel_changed",
                    locale=after.preferred_locale,
                    values=(
                        before.public_updates_channel.mention,
                        before.public_updates_channel.name,
                        after.public_updates_channel.mention,
                        after.public_updates_channel.name
                    )
                )

        if before.region != after.region:
            embed.description += _t.get(
                key="logging.on_guild_update.region_changed",
                locale=after.preferred_locale,
                values=(before.region, after.region)
            )

        if before.rules_channel != after.rules_channel:
            if before.rules_channel is None and after.rules_channel is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.rules_channel_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.rules_channel.mention, after.rules_channel.name)
                )

            elif before.rules_channel is not None and after.rules_channel is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.rules_channel_removed",
                    locale=after.preferred_locale,
                    values=(before.rules_channel.mention, before.rules_channel.name, not_ind)
                )
            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.rules_channel_removed",
                    locale=after.preferred_locale,
                    values=(
                        before.rules_channel.mention,
                        before.rules_channel.name,
                        after.rules_channel.mention,
                        after.rules_channel.name,
                    )
                )

        if before.safety_alerts_channel != after.safety_alerts_channel:
            if before.safety_alerts_channel is None and after.safety_alerts_channel is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.safety_alerts_channel_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.safety_alerts_channel.mention, after.safety_alerts_channel.name)
                )

            elif before.safety_alerts_channel is not None and after.safety_alerts_channel is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.safety_alerts_channel_removed",
                    locale=after.preferred_locale,
                    values=(before.safety_alerts_channel.mention, before.safety_alerts_channel.name, not_ind)
                )

            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.safety_alerts_channel_changed",
                    locale=after.preferred_locale,
                    values=(
                        before.safety_alerts_channel.mention,
                        before.safety_alerts_channel.name,
                        after.safety_alerts_channel.mention,
                        after.safety_alerts_channel.name
                    )
                )

        if before.system_channel != after.system_channel:
            if before.system_channel is None and after.system_channel is not None:
                embed.description += _t.get(
                    key="logging.on_guild_update.system_channel_added",
                    locale=after.preferred_locale,
                    values=(not_ind, after.system_channel.mention, after.system_channel.name)
                )

            elif before.system_channel is not None and after.system_channel is None:
                embed.description += _t.get(
                    key="logging.on_guild_update.system_channel_removed",
                    locale=after.preferred_locale,
                    values=(before.system_channel.mention, before.system_channel.name, not_ind)
                )

            else:
                embed.description += _t.get(
                    key="logging.on_guild_update.system_channel_changed",
                    locale=after.preferred_locale,
                    values=(
                        before.system_channel.mention,
                        before.system_channel.name,
                        after.system_channel.mention,
                        after.system_channel.name
                    )
                )

        if before.system_channel_flags != after.system_channel_flags:
            embed.description += _t.get(
                key="logging.on_guild_update.system_channel_flags_changed",
                locale=after.preferred_locale
            )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_bulk_message_delete(self, messages: List[Message]) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=messages[0].guild)
            channel_send: TextChannel | None = messages[0].guild.get_channel(settings[4])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        deleter: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.message_bulk_delete
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_bulk_message.title", locale=messages[0].guild.preferred_locale),
            description=_t.get(
                key="logging.on_bulk_message_delete.embed.description",
                locale=messages[0].guild.preferred_locale,
                values=(
                    deleter[0].user.mention,
                    deleter[0].user,
                    messages[0].channel.mention,
                    messages[0].channel.name,
                    len(messages)
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_invite_create(self, invite: Invite) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=invite.guild)
            channel_send: TextChannel | None = invite.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_invite.title", locale=invite.guild.preferred_locale),
            description=_t.get(
                key="logging.on_invite_create.embed.description",
                locale=invite.guild.preferred_locale,
                values=(
                    invite.inviter.mention,
                    invite.inviter,
                    invite.channel.mention,
                    invite.channel.name,
                    invite.code,
                    format_dt(invite.expires_at),
                    invite.max_uses
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_invite_delete(self, invite: Invite) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=invite.guild)
            channel_send: TextChannel | None = invite.guild.get_channel(settings[1])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        deleter: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.invite_delete
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_invite.title", locale=invite.guild.preferred_locale),
            description=_t.get(
                key="logging.on_invite_delete.embed.description",
                locale=invite.guild.preferred_locale,
                values=(
                    deleter[0].user.mention,
                    deleter[0].user,
                    invite.channel.mention,
                    invite.channel.name,
                    invite.code,
                    format_dt(invite.expires_at),
                    invite.uses,
                    invite.max_uses
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_member_join(self, member: Member) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=member.guild)
            channel_send: TextChannel | None = member.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_member.title", locale=member.guild.preferred_locale),
            description=_t.get(
                key="logging.on_member_join.embed.description",
                locale=member.guild.preferred_locale,
                values=(
                    member.mention,
                    member,
                    format_dt(member.created_at, style='R')
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_member_remove(self, member: Member) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=member.guild)
            channel_send: TextChannel | None = member.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        try:
            await member.guild.fetch_ban(member)
        except NotFound:
            embed: EmbedUI = EmbedUI(
                title=_t.get(key="logging.on_member.title", locale=member.guild.preferred_locale),
                description=_t.get(
                    key="logging.on_member_remove.embed.description",
                    locale=member.guild.preferred_locale,
                    values=(
                        member.mention,
                        member,
                        format_dt(member.joined_at, style='R'),
                        format_dt(member.created_at, style='R')
                    )
                )
            )

            try:
                await channel_send.send(embed=embed)
            except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
                pass
        else:
            return

    @CogUI.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        if before.roles != after.roles:
            return

        not_ind: str = _t.get(key="logging.not_indicated", locale=before.guild.preferred_locale)

        description = _t.get(
            key="logging.on_member_update.embed.description",
            locale=after.guild.preferred_locale,
            values=(
                after.mention,
                after
            )
        )
        embed: EmbedUI = EmbedUI(
            title=_t.get(
                key="logging.on_member.title",
                locale=before.guild.preferred_locale
            ),
            description=description
        )

        if before.nick != after.nick:
            embed.description += _t.get(
                key="logging.on_member_update.nick_change",
                locale=after.guild.preferred_locale,
                values=(
                    before.nick,
                    after.nick
                )
            )

        if before.display_avatar != after.display_avatar:
            if before.display_avatar is not None and after.display_avatar is not None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_changed",
                    locale=before.guild.preferred_locale,
                    values=(before.display_avatar.url, after.display_avatar.url)
                )

            elif before.display_avatar is None and after.display_avatar is not None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_added",
                    locale=before.guild.preferred_locale,
                    values=(not_ind, after.display_avatar.url)
                )

            elif before.display_avatar is not None and after.display_avatar is None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_removed",
                    locale=before.guild.preferred_locale,
                    values=(before.display_avatar.url, not_ind)
                )

        if before.display_avatar_decoration != after.display_avatar_decoration:
            if before.display_avatar_decoration is not None and after.display_avatar_decoration is not None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_decoration_changed",
                    locale=before.guild.preferred_locale,
                    values=(before.display_avatar_decoration.url, after.display_avatar_decoration.url)
                )

            elif before.display_avatar_decoration is None and after.display_avatar_decoration is not None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_decoration_added",
                    locale=before.guild.preferred_locale,
                    values=(not_ind, after.display_avatar_decoration.url)
                )

            elif before.display_avatar_decoration is not None and after.display_avatar_decoration is None:
                embed.description += _t.get(
                    key="logging.on_member_update.guild_avatar_decoration_removed",
                    locale=before.guild.preferred_locale,
                    values=(before.display_avatar_decoration.url, not_ind)
                )

        if embed.description == description:
            return

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_message_delete(self, message: Message) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=message.guild)
            channel_send: TextChannel | None = message.guild.get_channel(settings[4])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        if message.author.bot:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_message.title", locale=message.guild.preferred_locale),
            description=_t.get(
                key="logging.on_message_delete.embed.description",
                locale=message.guild.preferred_locale,
                values=(
                    message.author.mention,
                    message.author,
                    message.channel.mention,
                    message.channel.name,
                    message.jump_url,
                    message.content
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[4])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        if before.author.bot:
            return

        if before.flags != after.flags:
            return

        if before.pinned != after.pinned:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_message.title", locale=before.guild.preferred_locale),
            description=_t.get(
                key="logging.on_message_edit.embed.description",
                locale=after.guild.preferred_locale,
                values=(
                    after.author.mention,
                    after.author,
                    after.channel.mention,
                    after.channel.name,
                    after.jump_url
                )
            )
        )

        if before.content != after.content:
            embed.description += _t.get(
                key="logging.on_message_edit.content_changed",
                locale=after.guild.preferred_locale,
                values=(before.content, after.content)
            )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_reaction_add(self, reaction: Reaction, user: Member | User) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=reaction.message.guild)
            channel_send: TextChannel | None = reaction.message.guild.get_channel(settings[4])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_reaction.title", locale=reaction.message.guild.preferred_locale),
            description=_t.get(
                key="logging.on_reaction_add.embed.description",
                locale=reaction.message.guild.preferred_locale,
                values=(
                    user.mention,
                    user,
                    reaction.message.channel.mention,
                    reaction.message.channel.name,
                    reaction.message.jump_url,
                    reaction
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_reaction_remove(self, reaction: Reaction, user: Member | User) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=reaction.message.guild)
            channel_send: TextChannel | None = reaction.message.guild.get_channel(settings[4])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_reaction.title", locale=reaction.message.guild.preferred_locale),
            description=_t.get(
                key="logging.on_reaction_remove.embed.description",
                locale=reaction.message.guild.preferred_locale,
                values=(
                    user.mention,
                    user,
                    reaction.message.channel.mention,
                    reaction.message.channel.name,
                    reaction.message.jump_url,
                    reaction
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_thread_create(self, thread: Thread) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=thread.guild)
            channel_send: TextChannel | None = thread.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_thread.title", locale=thread.guild.preferred_locale),
            description=_t.get(
                key="logging.on_thread_create.embed.description",
                locale=thread.guild.preferred_locale,
                values=(
                    thread.owner.mention,
                    thread.owner.name,
                    thread.jump_url,
                    thread.name,
                    thread.parent.mention,
                    thread.parent.name
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_thread_delete(self, thread: Thread) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=thread.guild)
            channel_send: TextChannel | None = thread.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        deleter: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.thread_delete
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_thread.title", locale=thread.guild.preferred_locale),
            description=_t.get(
                key="logging.on_thread_delete.embed.description",
                locale=thread.guild.preferred_locale,
                values=(
                    deleter[0].user.mention,
                    deleter[0].user,
                    thread.jump_url,
                    thread.name,
                    thread.parent.mention,
                    thread.parent.name
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_thread_member_join(self, member: ThreadMember) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=member.thread.guild)
            channel_send: TextChannel | None = member.thread.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        _member: Member = member.thread.guild.get_member(member.id)

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_thread.title", locale=member.thread.guild.preferred_locale),
            description=_t.get(
                key="logging.on_thread_member_join.embed.description",
                locale=_member.guild.preferred_locale,
                values=(
                    _member.mention,
                    _member,
                    member.thread.jump_url,
                    member.thread.name,
                    member.thread.parent.mention,
                    member.thread.parent.name
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_thread_member_remove(self, member: ThreadMember) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=member.thread.guild)
            channel_send: TextChannel | None = member.thread.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        _member: Member = member.thread.guild.get_member(member.id)

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_thread.title", locale=member.thread.guild.preferred_locale),
            description=_t.get(
                key="logging.on_thread_member_remove.embed.description",
                locale=_member.guild.preferred_locale,
                values=(
                    _member.mention,
                    _member,
                    member.thread.jump_url,
                    member.thread.name,
                    member.thread.parent.mention,
                    member.thread.parent.name
                )
            )
        )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_thread_update(self, before: Thread, after: Thread) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=before.guild)
            channel_send: TextChannel | None = before.guild.get_channel(settings[2])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        updater: list[AuditLogEntry] = await channel_send.guild.audit_logs(
            limit=1,
            action=AuditLogAction.thread_delete
        ).flatten()

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_thread.title", locale=before.guild.preferred_locale),
            description=_t.get(
                key="logging.on_thread_update.embed.description",
                locale=before.guild.preferred_locale,
                values=(
                    updater[0].user.mention,
                    updater[0].user,
                    after.jump_url,
                    after.name,
                    after.parent.mention,
                    after.parent.name
                )
            )
        )

        if before.name != after.name:
            embed.description += _t.get(
                key="logging.on_thread_update.name_changed",
                locale=before.guild.preferred_locale,
                values=(before.name, after.name)
            )

        if before.locked != after.locked:
            embed.description += _t.get(
                key="logging.on_thread_update.locked_changed",
                locale=before.guild.preferred_locale,
                values=(before.locked, after.locked)
            )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass

    @CogUI.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        try:
            settings: Record = await self.bot.databases.settings.get_logs_settings(guild=member.guild)
            channel_send: TextChannel | None = member.guild.get_channel(settings[3])
        except Exception as e:
            _ = e
            return None

        if channel_send is None:
            return

        embed: EmbedUI = EmbedUI(
            title=_t.get(key="logging.on_member.title", locale=member.guild.preferred_locale),
            description=_t.get(
                key="logging.on_voice_state_update.embed.description",
                locale=member.guild.preferred_locale,
                values=(member.mention, member)
            )
        )

        not_ind: str = _t.get(key="logging.not_indicated", locale=member.guild.preferred_locale)

        if before.channel == after.channel:
            embed.description += _t.get(
                key="logging.on_voice_state_update.channel_unchanged",
                locale=member.guild.preferred_locale,
                values=(after.channel.mention, after.channel.name)
            )

            if before.self_mute != after.self_mute:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.self_mute_changed",
                    locale=member.guild.preferred_locale,
                    values=(before.self_mute, after.self_mute)
                )

            if before.self_stream != after.self_stream:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.self_stream_changed",
                    locale=member.guild.preferred_locale,
                    values=(before.self_stream, after.self_stream)
                )

            if before.self_video != after.self_video:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.self_video_changed",
                    locale=member.guild.preferred_locale,
                    values=(before.self_video, after.self_video)
                )
        else:
            if before.channel is not None and after.channel is not None:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.channel_changed",
                    locale=member.guild.preferred_locale,
                    values=(before.channel.mention, before.channel.name, after.channel.mention, after.channel.name)
                )

            elif before.channel is None and after.channel is not None:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.channel_joined",
                    locale=member.guild.preferred_locale,
                    values=(not_ind, after.channel.mention, after.channel.name)
                )

            elif before.channel is not None and after.channel is None:
                embed.description += _t.get(
                    key="logging.on_voice_state_update.channel_left",
                    locale=member.guild.preferred_locale,
                    values=(before.channel.mention, before.channel.name, not_ind)
                )

        try:
            await channel_send.send(embed=embed)
        except (HTTPException, Forbidden, TypeError, ValueError, AttributeError):
            pass


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(LoggingCog(bot))

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from datetime import datetime
from random import choice
from typing import TYPE_CHECKING, Optional

from disnake import (
    NotFound,
    HTTPException,
    Forbidden,
    VoiceChannel,
    Member,
    Activity,
    Game,
    CustomActivity,
    Streaming,
    Spotify, Guild, User, Message
)
from disnake.ext.tasks import loop
from loguru import logger

from utils.basic import CogUI, IntFormatter, EmbedUI
from utils.basic.services.draw import DrawService
from utils.basic.services.draw.types import ContentType
from utils.consts import ERROR_EMOJI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class Banners(CogUI):
    def __init__(self, bot: ChisatoBot) -> None:
        super().__init__(bot)

        self.most_active: dict[Guild, dict[Member, int]] = defaultdict(defaultdict)

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()

        self.banner_change_task.start()
        self.check_boosts.start()
        self.clear_most_activity.start()

    def cog_unload(self) -> None:
        self.banner_change_task.cancel()
        self.check_boosts.cancel()
        self.clear_most_activity.cancel()

    @loop(hours=2)
    async def clear_most_activity(self) -> None:
        self.most_active.clear()

    @loop(minutes=2)
    async def check_boosts(self) -> None:
        if hasattr(self.bot.databases, "settings"):
            if rows := await self.bot.databases.settings.get_guilds_with_banners():
                for row in rows:
                    if guild_obj := self.bot.get_guild(row[0]):
                        if guild_obj.premium_subscription_count <= 6:
                            await self.bot.databases.settings.remove(banner=True, guild=row[0])

    @CogUI.listener("on_message")
    async def read_message(self, message: Message) -> None:
        if isinstance(message.author, User) or message.author.bot:
            return

        if self.most_active[message.guild].get(message.author):
            self.most_active[message.guild][message.author] += 1
        else:
            self.most_active[message.guild][message.author] = 1

    def get_most_activity_member(self, guild: Guild) -> Optional[Member]:
        if self.most_active[guild].keys():
            return list(sorted(
                self.most_active[guild].items(),
                key=lambda x: x[1],
                reverse=True
            ))[0][0]
        return None

    @classmethod
    def get_voice_members(cls, channels: list[VoiceChannel]) -> int:
        return sum(len(channel.members) for channel in channels)

    @staticmethod
    def remove_emojis(text: str) -> str:
        return re.sub(r'[^\x00-\x7F]+', '', text).lstrip()

    @classmethod
    def get_member_activity(cls, member: Member) -> str:
        if isinstance(member.activity, Game):
            playing_on = _t.get(
                "banners.activity.game",
                locale=member.guild.preferred_locale
            )
            return playing_on + member.activity.name
        elif isinstance(member.activity, Streaming):
            streaming = _t.get(
                "banners.activity.streaming",
                locale=member.guild.preferred_locale
            )
            return streaming + str(member.activity.game)
        elif isinstance(member.activity, Spotify):
            listening = _t.get(
                "banners.activity.listening",
                locale=member.guild.preferred_locale
            )
            return listening + str(member.activity.title)
        elif (
                isinstance(member.activity, CustomActivity)
                or isinstance(member.activity, Activity)
        ):
            return member.activity.name
        else:
            return _t.get(
                "banners.activity.relaxing",
                locale=member.guild.preferred_locale
            )

    async def _change_banner_task_background(
            self,
            guild: Guild,
            banner_name: str
    ) -> None:
        if not await DrawService(self.bot.session).get_status():
            await self.bot.webhooks.post(
                {
                    "embed": EmbedUI(
                        title=f"{ERROR_EMOJI} Проблема с API",
                        description=f"> **Причина:** `API не дает ответа.`\n"
                                    f"> **Гильдия:** `{guild.name} | {guild.id} ({guild.owner.name} "
                                    f"| {guild.owner.id})`\n"
                                    f"> **Время:** {(n := datetime.now())} | `{n.timestamp()}`"
                    )
                },
                type='command'
            )
            return logger.warning("Api offline... Banner don't changed background")

        member = (
                self.get_most_activity_member(guild)
                or choice(sum(map(lambda channel: channel.members, guild.voice_channels), []) or guild.members)
        )
        async with DrawService(self.bot.session) as r:
            file = await r.draw_image(
                "guild_banner",
                cache=False,
                content_type=ContentType.BYTES,
                bannerName=banner_name,
                guildLanguage=str(guild.preferred_locale).replace("-", "_"),
                guildMembers=m if (
                                      m := len(guild.members)
                                  ) < 999999 else IntFormatter(m).format_number(),
                voiceMembers=v if (
                                      v := self.get_voice_members(guild.voice_channels)
                                  ) < 9999 else IntFormatter(v).format_number(),
                activityMemberAvatarUrl=member.display_avatar.url,
                activityMemberName=member.name,
                activityMemberStatus=choice(
                    _t.get(
                        "banners.activities.list",
                        locale=guild.preferred_locale
                    )
                )
            )

        try:
            await guild.edit(banner=file)
        except NotFound:
            pass
        except Forbidden:
            pass
        except HTTPException as e:
            logger.warning(f"{e.__class__.__name__}: {e}")

    @loop(minutes=1)
    async def banner_change_task(self) -> None:
        if not hasattr(self.bot.databases, "settings"):
            return

        for guild_id, banner_name in (
                await self.bot.databases.settings.get_guilds_with_banners()
        ):
            if guild := self.bot.get_guild(guild_id):
                asyncio.create_task(
                    self._change_banner_task_background(
                        guild, banner_name
                    )
                )


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(Banners(bot))

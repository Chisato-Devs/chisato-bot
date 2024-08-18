from __future__ import annotations

from typing import Union, TYPE_CHECKING

from disnake import (
    Member,
    HTTPException,
    Forbidden,
    ui,
    Embed,
    Guild,
    TextChannel,
    VoiceChannel,
    StageChannel,
    Thread,
    PartialMessageable
)

from utils.basic import (
    EmbedUI
)
from utils.dataclasses import Pet
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

GuildMessageable = Union[TextChannel, Thread, VoiceChannel, StageChannel]
_t = ChisatoLocalStore.load("./cogs/economy/pets.py")


class OwnerAlertManager:
    def __init__(self, bot: ChisatoBot) -> None:
        self.bot: ChisatoBot = bot

    async def send_member(self, member: Member, guild: Guild, embed: Embed) -> None:
        try:
            if await self.bot.databases.pets.owner_alert(guild=guild.id, member=member.id):
                await member.send(
                    embed=embed, components=[
                        ui.Button(
                            label=_t.get(
                                "pets.sent_from_guild", locale=guild.preferred_locale,
                                values=(guild.name,)
                            ),
                            emoji='<:Messagebox:1131481077052080149>', disabled=True
                        )
                    ]
                )
        except Forbidden:
            pass
        except HTTPException:
            pass

    async def pet_owner_alert_low_stat(
            self, member: Member, guild: Guild, channel: Union[GuildMessageable, PartialMessageable] = None
    ) -> None:
        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=guild.id, member=member.id)
        pet_titles = _t.get("pets.dict.titles", locale=guild.preferred_locale)

        await self.send_member(
            member, guild, EmbedUI(
                title=pet_titles[pet_info.name],
                description=_t.get(
                    "pets.low_stats.dm",
                    locale=guild.preferred_locale
                )
            )
        )

        if channel:
            try:
                await channel.send(
                    embed=EmbedUI(
                        title=pet_titles[pet_info.name],
                        description=_t.get(
                            "pets.low_stats.channel",
                            locale=guild.preferred_locale,
                            values=(member.display_name,)
                        )
                    )
                )
            except Forbidden:
                pass
            except HTTPException:
                pass

    async def pet_owner_alert_reached_max_lvl(
            self, member: Member, guild: Guild, channel: Union[GuildMessageable, PartialMessageable] = None
    ) -> None:
        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=guild.id, member=member.id)
        pet_titles = _t.get("pets.dict.titles", locale=guild.preferred_locale)

        await self.send_member(
            member, guild, EmbedUI(
                title=pet_titles[pet_info.name],
                description=_t.get("pets.reached_max.dm", locale=guild.preferred_locale)
            )
        )

        if channel:
            try:
                await channel.send(
                    embed=EmbedUI(
                        title=pet_titles[pet_info.name],
                        description=_t.get(
                            "pets.reached_max.channel", locale=guild.preferred_locale,
                            values=(member.display_name,)
                        )
                    )
                )
            except Forbidden:
                pass
            except HTTPException:
                pass

    async def pet_owner_alert_died(
            self, member: Member, guild: Guild, channel: Union[GuildMessageable, PartialMessageable] = None
    ) -> None:
        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=guild.id, member=member.id)
        pet_titles = _t.get("pets.dict.titles", locale=guild.preferred_locale)

        await self.send_member(
            member, guild, EmbedUI(
                title=pet_titles[pet_info.name],
                description=_t.get("pets.cattery.dm", locale=guild.preferred_locale)
            )
        )

        if channel:
            try:
                await channel.send(
                    embed=EmbedUI(
                        title=pet_titles[pet_info.name],
                        description=_t.get(
                            "pets.cattery.channel", locale=guild.preferred_locale,
                            values=(member.display_name,)
                        )
                    )
                )
            except Forbidden:
                pass
            except HTTPException:
                pass

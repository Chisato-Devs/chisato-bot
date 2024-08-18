from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from disnake import Guild, Member, User, TextChannel, VoiceChannel, ForumChannel, StageChannel, \
    ApplicationCommandInteraction, Localized, Message, HTTPException, Forbidden
from disnake.ext.commands import Param, has_permissions
from loguru import logger

from utils.basic import CogUI, EmbedUI, EmbedErrorUI
from utils.basic.services.draw import DrawService
from utils.handlers.entertainment.levels import levels_on
from utils.handlers.entertainment.levels.utils import RankCard
from utils.handlers.entertainment.levels.views import PrestigeView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class Levels(CogUI):

    @CogUI.slash_command(name="rank")
    @levels_on()
    async def _rank(self, interaction: ApplicationCommandInteraction) -> None:
        pass

    @_rank.sub_command(
        name="card",
        description=Localized(
            "💫 Ранги: показать карточку ранга",
            data=_t.get("level.command.show_card")
        )
    )
    async def card(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("level.commands_option.member.name")),
                description=Localized("- выбери участника", data=_t.get("level.commands_option.member.description")),
                default=lambda x: x.author
            )
    ) -> None:
        if not await DrawService(self.bot.session).get_status():
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "fun.errors.api_error", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        elif member.bot:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "level.error.is_bot",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await self.bot.databases.level.add_member_to_table(guild=interaction.guild.id, member=member.id)
        file = await RankCard.draw(interaction, member)

        if interaction.author.id == member.id and (await self.bot.databases.level.check_now_prestige(
                guild=interaction.guild.id, member=interaction.author.id
        )):
            await interaction.response.send_message(
                file=file, view=PrestigeView(
                    interaction.author, interaction=interaction
                )
            )
        else:
            await interaction.response.send_message(file=file)

    @_rank.sub_command(
        name="set", description=Localized(
            "💫 Ранги: установить уровень",
            data=_t.get("level.command.set_card")
        )
    )
    @has_permissions(administrator=True)
    async def set(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("level.commands_option.member.name")),
                description=Localized(
                    "- выбери участника",
                    data=_t.get("level.commands_option.member.description")
                ),
                default=lambda x: x.author
            ),
            prestige: int = Param(
                name=Localized("престиж", data=_t.get("level.commands_option.prestige.name")),

                description=Localized(
                    "- укажи число для установления престижа",
                    data=_t.get("level.commands_option.prestige.description")
                ),
                min_value=0, max_value=10, default=None
            ),
            level: int = Param(
                name=Localized("уровень", data=_t.get("level.commands_option.level.name")),
                description=Localized(
                    "- укажи число для установления уроня",
                    data=_t.get("level.commands_option.level.description")
                ),
                min_value=1, max_value=100, default=None
            )
    ) -> None:
        if not (level or prestige):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "level.not_level_or_prestige.embed_error.description", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        elif member.bot:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "level.error.is_bot",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await self.bot.databases.level.add_member_to_table(guild=interaction.guild.id, member=member.id)

        setted = []
        if level:
            await self.bot.databases.level.set_level(id=level, guild=interaction.guild.id, member=member.id)
            setted.append(_t.get("level.commands_option.member.name", locale=interaction.guild_locale))

        if prestige:
            await self.bot.databases.level.set_prestige(id=prestige, guild=interaction.guild.id, member=member.id)
            setted.append(_t.get("level.commands_option.prestige.name", locale=interaction.guild_locale))

        desc = _t.get(
            key="level.command.set.embed.description", locale=interaction.guild_locale,
            values=('и '.join(setted), interaction.author.mention, interaction.author)
        )

        if level:
            desc += _t.get(
                key="level.command.set.embed.description.part_1", locale=interaction.guild_locale,
                values=(level, level)
            )

        if prestige:
            desc += _t.get(
                key="level.command.set.embed.description.part_2", locale=interaction.guild_locale,
                values=(prestige, prestige)
            )

        embed = EmbedUI(
            title=_t.get("fun.success.title", locale=interaction.guild_locale),
            description=desc,
            timestamp=interaction.created_at
        )
        await interaction.response.send_message(embed=embed)

    @CogUI.listener("on_member_level_upped")
    async def member_level_upped(
            self, guild: Guild, member: Member,
            channel: TextChannel | VoiceChannel | ForumChannel | StageChannel
    ) -> None:
        if (
                (settings_values := await self.bot.databases.level.settings_values(guild=guild.id))
                and settings_values[2] and settings_values[1]
        ):
            user_data = await self.bot.databases.level.select_data(
                guild=guild.id, member=member.id
            )

            if settings_values[3]:
                embeds = [
                    EmbedUI.from_dict_with_attrs(
                        embed_data=embed_data,
                        attrs={
                            "member": member.name,
                            "last_rank": user_data[3] - 1,
                            "rank": user_data[3],
                            "now_exp": user_data[5],
                            "need_exp": user_data[4],
                            "prestige": user_data[2],
                            "member_avatar": member.display_avatar.url[8:],
                            "can_prestige": _t.get(
                                "level.available" if user_data[3] == 100
                                else "level.not_available",
                                locale=guild.preferred_locale
                            )
                        }
                    )
                    for embed_data in ast.literal_eval(settings_values[3])
                ]
            else:
                embeds = [EmbedUI(
                    title=_t.get(
                        "level.system.title",
                        locale=guild.preferred_locale
                    ),
                    description=_t.get(
                        key="level.up_level.embed.description",
                        locale=guild.preferred_locale,
                        values=(
                            member.mention, member, user_data[2],
                            _t.get(
                                "level.available" if user_data[3] == 100
                                else "level.not_available",
                                locale=guild.preferred_locale
                            ),
                            user_data[3], user_data[4]
                        )
                    )
                )]
            try:
                await channel.send(content=f'|| {member.mention} ||', embeds=embeds)
            except Forbidden:
                pass
            except HTTPException as e:
                logger.warning(f"{HTTPException.__name__}: {e}")

    @CogUI.listener('on_message')
    async def add_exp(self, message: Message) -> None:
        if isinstance(message.author, User) or message.author.bot:
            return

        try:
            await self.bot.databases.level.passive_exp(
                guild=message.guild,
                member=message.author,
                channel=message.channel,
                bot=self.bot
            )
        except Exception as e:
            logger.warning(f"{type(e).__name__}: {e}")


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(Levels(bot))

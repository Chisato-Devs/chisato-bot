from disnake import ui, ButtonStyle, Forbidden, Guild
from loguru import logger

from utils.basic import EmbedUI, ChisatoBot, CogUI
from utils.consts import LINK_EMOJI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)


class GuildAnalytics(CogUI):

    @CogUI.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        if self.bot.user.id != env.MAIN_ID:
            return

        try:
            await self.bot.databases.vipe_tables_from_guild(guild)
        except Exception as e:
            logger.warning(
                f"GUILD KICKED RAISED AN EXCEPTION {type(e).__name__}: {e}"
            )

        if not guild.owner:
            return logger.warning(f"BOT REMOVED FROM GUILD: {guild.name} ({guild.id})")

        await self.bot.webhooks.post(
            data={
                'embed': EmbedUI(
                    title=f'{LINK_EMOJI} Контроль гильдий',
                    description=f'Бота выгнали с сервера!\n'
                                f'> **Название**: `{guild.name}`\n'
                                f'> **Участников:** `{len(guild.members)}`\n'
                                f'> **Каналов:** `{len(guild.channels)}`\n'
                                f'> **Ролей:** `{len(guild.roles)}`\n'
                                f'> **Владелец**: {guild.owner.global_name} (`{guild.owner.id} | {guild.owner.name}`)\n'
                                f'> **Отвечающий шард**: `{guild.shard_id}`\n'
                                f'> **Войс клиент**: `{"Активен" if guild.voice_client else "Неактивен"}`'
                )
            }, type='guild_control'
        )
        await self.bot.databases.admin.reg_to_analytics(
            f"Бота выгнали с гильдии",
            GuildName=guild.name,
            Owner=str(guild.owner),
            MemberCount=str(guild.member_count)
        )

    @CogUI.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        if self.bot.user.id != env.MAIN_ID:
            return

        if not guild.owner:
            return logger.warning(f"BOT ADDED TO GUILD: {guild.name} ({guild.id})")

        await self.bot.webhooks.post(
            data={
                'embed': EmbedUI(
                    title=f'{LINK_EMOJI} Контроль гильдий',
                    description=f'Бот добавлен на сервер!\n'
                                f'> **Название**: `{guild.name}`\n'
                                f'> **Участников:** `{len(guild.members)}`\n'
                                f'> **Каналов:** `{len(guild.channels)}`\n'
                                f'> **Ролей:** `{len(guild.roles)}`\n'
                                f'> **Владелец**: {guild.owner.global_name} (`{guild.owner.id} | {guild.owner.name}`)\n'
                                f'> **Отвечающий шард**: `{guild.shard_id}`\n'
                )
            },
            type='guild_control'
        )

        await self.bot.databases.admin.reg_to_analytics(
            f"Бота добавили на гильдию",
            GuildName=guild.name,
            Owner=str(guild.owner),
            MemberCount=str(guild.member_count)
        )

        try:
            await guild.text_channels[0].send(
                embed=EmbedUI(
                    title=_t.get("guild_control.new_guild.embed.title", locale=guild.preferred_locale),
                    description=_t.get("guild_control.new_guild.embed.description", locale=guild.preferred_locale)
                ).set_thumbnail(url=self.bot.user.avatar.url),
                components=[
                    ui.Button(
                        label=_t.get("guild_control.new_guild.component.label", locale=guild.preferred_locale),
                        style=ButtonStyle.url, url="https://discord.com/invite/JPVMn3jyAc"
                    )
                ]
            )
        except Forbidden:
            pass


def setup(bot: ChisatoBot) -> None:
    bot.add_cog(GuildAnalytics(bot))
